"""
Production-ready MCP Client for Pipedream Integration
Connects to 32+ enterprise applications via Pipedream's remote MCP server
"""


import aiohttp
import uuid
import logging
from datetime import datetime
from typing import Any, Dict, Optional
import requests

from fastapi import Request

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipedreamMCPClient:
    """
    Enhanced Python client for Pipedream MCP server with OAuth flow handling.
    
    This client handles the complete OAuth flow including:
    - Generating authentication URLs
    - Opening the OAuth popup window
    - Handling the OAuth callback
    - Managing the access token
    """
    
    # Class-level variable to store the active popup window
    _popup_window = None
    
    def __init__(self, 
                 client_id: str,
                 client_secret: str, 
                 project_id: str,
                 environment: str = "development",
                 external_user_id: str = "",
                 app_slug: str = "",
                 server_url: Optional[str] = None,
                 access_token: Optional[str] = None):
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.project_id = project_id
        self.environment = environment
        self.external_user_id = external_user_id
        self.app_slug = app_slug
        self.server_url = server_url or "https://remote.mcp.pipedream.net"
        self._access_token = access_token
        self._oauth_states = {}  # Track OAuth states for validation
        
    async def get_available_apps(self) -> list[dict]:
        """
        Fetch the list of available apps with their metadata from app_info.json
        
        Returns:
            list[dict]: List of app objects with metadata including name, slug, logo_url, and categories
        """
        try:
            from ..utils import read_app_info
            
            # Read app info from the JSON file
            app_info = read_app_info()
            
            if not app_info:
                logger.warning("No app info found in app_info.json")
                return []
                
            # Filter apps based on MCP_APPS if needed
            # For now, return all apps from the file
            return app_info
            
        except Exception as e:
            logger.error(f"Error reading app info: {str(e)}")
            # Fallback to a basic list if there's an error
            return [
                {
                    "app_slug": "github",
                    "name": "GitHub",
                    "logo_url": "https://assets.pipedream.net/s.v0/app_OrZhaO/logo/orig",
                    "app_category": ["Developer Tools"],
                    "description": "Where the world builds software"
                },
                {
                    "app_slug": "slack",
                    "name": "Slack",
                    "logo_url": "https://assets.pipedream.net/s.v0/app_1P8h4m/logo/orig",
                    "app_category": ["Communication"],
                    "description": "Slack brings all your communication together"
                }
            ]
        self._session = None  # Will store aiohttp session for connection reuse
    
    def parse_sse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Server-Sent Events response format"""
        lines = [line.strip() for line in response_text.split('\n') if line.strip()]
        result = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                result[key.strip().lower()] = value.strip()
                
        return result
    
    def get_headers(self) -> Dict[str, str]:
        """Get default headers for MCP requests"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",  # For SSE
            "X-Pipedream-Client": "mcp-python-sdk/1.0.0",
            "Connection": "close",  # Don't keep connection alive
        }
        
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
            
        return headers
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
        
    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request to the Pipedream API"""
        url = f"{self.server_url}{endpoint}"
        headers = kwargs.pop('headers', {})
        
        # Add auth headers if we have a token
        if self._access_token and 'Authorization' not in headers:
            headers['Authorization'] = f"Bearer {self._access_token}"
            
        # Add content type if not specified
        if 'Content-Type' not in headers and method.lower() in ['post', 'put', 'patch']:
            headers['Content-Type'] = 'application/json'
            
        try:
            session = await self._get_session()
            async with session.request(method, url, headers=headers, **kwargs) as response:
                response.raise_for_status()
                
                # Handle different response types
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    return await response.json()
                else:
                    return {'data': await response.text()}
                        
        except aiohttp.ClientError as e:
            logger.error(f"Request failed: {str(e)}")
            raise

    async def initialize_session(self) -> Dict[str, Any]:
        """Initialize MCP session"""
        payload = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "pipedream-python-client",
                    "version": "1.0.0"
                }
            }
        }
        
        return await self._make_request('POST', '/', json=payload)
    
    async def get_app_connect_token(self, user_id: str, project_id: str) -> str:
        """Get the connect token for every app connection"""
        
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "X-PD-Environment": "development"  # or "production" if you want the production env
        }
        body = {
            "external_user_id": user_id,
        }
        token_url = f"https://api.pipedream.com/v1/connect/{project_id}/tokens"
        resp = requests.post(token_url, headers=headers, json=body)
        connect_token = resp.json()["token"]
        return connect_token

            
    async def initialize_connection(self, user_id: str, project_id: str,app_slug: str = None) -> str:
        """
        Initialize a connection to the MCP server and get the OAuth URL.
        
        Args:
            user_id: The ID of the user initiating the connection
            state: Optional state parameter for OAuth flow
            app_slug: The slug of the app to connect to
            
        Returns:
            str: The OAuth URL to redirect the user to
        """
        # Generate a state token if not provided

        connect_token = await self.get_app_connect_token(user_id, project_id)

        connect_link = (
            f"https://pipedream.com/_static/connect.html?token={connect_token}&connectLink=true&app={app_slug}"
        )

        return connect_link
        

    async def list_tools(self) -> Dict[str, Any]:
        """List available tools from the MCP server"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        return await self._make_request('POST', '/', json=payload)
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool with arguments"""
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        return await self._make_request('POST', '/', json=payload)
    
    async def send_message(self, content: str, role: str = "user") -> Dict[str, Any]:
        """Send a message to the MCP server - first list tools, then call appropriate one"""
        # First, let's list available tools
        tools_result = await self.list_tools()
        
        if tools_result['status_code'] not in [200, 201]:
            return tools_result
        
        # Try to call a chat or message tool if available
        return await self.call_tool("chat", {
            "message": {
                "role": role,
                "content": content
            }
        })
    
    def get_oauth_popup_html(self, connect_url: str, callback_url: str = None, width: int = 600, height: int = 700) -> str:
        """
        Generate HTML/JS for an OAuth popup that handles the OAuth flow.
        
        Args:
            connect_url: The OAuth URL to open in the popup
            callback_url: Optional URL to redirect to after OAuth flow completes
            width: Width of the popup window
            height: Height of the popup window
            
        Returns:
            str: HTML content that can be served to handle the OAuth flow
        """
        # Generate a unique ID for this connection attempt
        import uuid
        popup_id = f"oauth_popup_{uuid.uuid4().hex[:8]}"
        
        app_slug = self.app_slug or 'the application'
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Connecting to {app_slug}...</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 20px; }}
                .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
                .btn {{ 
                    display: inline-block;
                    background: #4CAF50;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 4px;
                    margin: 10px 0;
                    cursor: pointer;
                }}
                .btn:hover {{ background: #45a049; }}
                .error {{ color: #d32f2f; }}
                .success {{ color: #388e3c; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Connecting to {self.app_slug}...</h2>
                <div id="status">
                    <p>Please wait while we redirect you to {self.app_slug} for authorization.</p>
                    <p>If you are not automatically redirected, please click the button below:</p>
                    <button id="openPopup" class="btn">Connect with {self.app_slug}</button>
                </div>
                <div id="message" style="margin-top: 20px;"></div>
            </div>

            <script>
                // Configuration
                const config = {{
                    connectUrl: '{connect_url}',
                    callbackUrl: '{callback_url}',
                    popupName: '{popup_id}',
                    popupFeatures: 'width={width},height={height},scrollbars=yes,resizable=yes,top=100,left=100'
                }};

                // DOM Elements
                const openPopupBtn = document.getElementById('openPopup');
                const statusDiv = document.getElementById('status');
                const messageDiv = document.getElementById('message');
                let popup = null;
                let popupCheckInterval = null;

                // Function to open the popup
                function openOAuthPopup() {{
                    // Try to open the popup
                    popup = window.open(
                        config.connectUrl,
                        config.popupName,
                        config.popupFeatures
                    );

                    if (!popup || popup.closed || typeof popup.closed === 'undefined') {{
                        // Popup was blocked or failed to open
                        showMessage('Popup was blocked. Please allow popups for this site and try again.', 'error');
                        openPopupBtn.style.display = 'inline-block';
                        return false;
                    }}

                    // Monitor the popup
                    popupCheckInterval = setInterval(checkPopup, 500);
                    openPopupBtn.style.display = 'none';
                    showMessage('Popup opened successfully. Please complete the authorization in the popup window.', 'success');
                    return true;
                }}

                // Function to check popup status
                function checkPopup() {{
                    if (!popup || popup.closed) {{
                        clearInterval(popupCheckInterval);
                        
                        // Check if we have a callback URL to redirect to
                        if (config.callbackUrl) {{
                            window.location.href = config.callbackUrl;
                        }}
                    }}
                }}

                // Function to show messages
                function showMessage(message, type = 'info') {{
                    messageDiv.innerHTML = `<p class="${{type}}">${{message}}</p>`;
                }}

                // Event Listeners
                openPopupBtn.addEventListener('click', openOAuthPopup);

                // Try to open the popup automatically when the page loads
                window.addEventListener('load', function() {{
                    // Small delay to ensure the page is fully loaded
                    setTimeout(openOAuthPopup, 100);
                }});

                // Handle messages from the popup (if needed)
                window.addEventListener('message', function(event) {{
                    if (event.origin !== window.location.origin) return;
                    
                    if (event.data && event.data.type === 'oauth_complete') {{
                        if (popup && !popup.closed) {{
                            popup.close();
                        }}
                        
                        if (config.callbackUrl) {{
                            window.location.href = config.callbackUrl;
                        }}
                    }}
                }});
            </script>
        </body>
        </html>
        """.format(
            connect_url=connect_url,
            callback_url=callback_url or '',
            width=width,
            height=height,
            app_slug=self.app_slug,
            popup_id=popup_id
        )
        
        return html
        
    async def handle_oauth_callback(self, request: 'Request' = None, code: str = None, state: str = None, error: str = None) -> Dict[str, Any]:
        """
        Handle the OAuth callback from the service provider.
        
        Args:
            request: The FastAPI request object (if available)
            code: The authorization code from the OAuth provider
            state: The state parameter from the OAuth provider
            error: Any error that occurred during OAuth
            
        Returns:
            Dict containing the result of the OAuth flow
        """
        try:
            # Get parameters from request if not provided directly
            if request:
                params = dict(request.query_params)
                code = code or params.get('code')
                state = state or params.get('state')
                error = error or params.get('error')
                
            # Handle OAuth errors
            if error:
                error_desc = request.query_params.get('error_description', 'No description provided') if request else 'No description provided'
                logger.error(f"OAuth error: {error} - {error_desc}")
                return {
                    'success': False,
                    'error': error,
                    'error_description': error_desc
                }
                
            # Validate state
            if not state or ':' not in state:
                logger.error(f"Invalid state format: {state}")
                return {
                    'success': False,
                    'error': 'invalid_state',
                    'error_description': 'Invalid state format'
                }
                
            # Extract user_id from state (format: "user_id:uuid")
            user_id, state_uuid = state.split(':', 1)
            
            # In a real implementation, you would validate the state against a stored value
            # For now, we'll just log it
            logger.info(f"Processing OAuth callback for user {user_id} with state {state}")
            
            # Exchange code for access token
            token_data = await self.exchange_code_for_token(code)
            
            # Get app_slug from the token data or state
            app_slug = token_data.get('app_slug')
            if not app_slug and ':' in state:
                # Try to get app_slug from state if not in token
                parts = state.split(':')
                if len(parts) > 2:
                    app_slug = parts[2]
            
            # Store the token (implementation depends on your storage)
            await self.store_token(user_id, app_slug or 'unknown', token_data)
            
            logger.info(f"Successfully authenticated user {user_id} for app {app_slug}")
            
            return {
                'success': True,
                'user_id': user_id,
                'app_slug': app_slug,
                'access_token': token_data.get('access_token'),
                'expires_in': token_data.get('expires_in'),
                'refresh_token': token_data.get('refresh_token')
            }
            
        except Exception as e:
            logger.error(f"Error handling OAuth callback: {str(e)}")
            return {
                'success': False,
                'error': 'server_error',
                'error_description': str(e)
            }
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange an authorization code for an access token.
        
        Args:
            code: The authorization code from the OAuth provider
            
        Returns:
            Dict containing the token data
        """
        token_url = "https://api.pipedream.com/v1/oauth/access_token"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._access_token}'
        }
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': f"{self.server_url}/auth/callback"
        }
        
        try:
            session = await self._get_session()
            async with session.post(token_url, headers=headers, json=data) as response:
                response.raise_for_status()
                token_data = await response.json()
                
                # Store the access token for future requests
                if 'access_token' in token_data:
                    self._access_token = token_data['access_token']
                
                return token_data
                    
        except aiohttp.ClientError as e:
            error_detail = f"Failed to exchange code for token: {str(e)}"
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                error_detail += f" - {await e.response.text()}"
            logger.error(error_detail)
            raise ConnectionError(error_detail)


# Factory function for easy initialization
def create_pipedream_client(**kwargs) -> PipedreamMCPClient:
    """Create a Pipedream MCP client with environment variables as defaults"""
    
    # You'll need to define these variables or pass them in kwargs
    config = {
        "client_id": kwargs.get("client_id", "your_client_id"),
        "client_secret": kwargs.get("client_secret", "your_client_secret"),
        "project_id": kwargs.get("project_id", "your_project_id"),
        "environment": kwargs.get("environment", "development"),
        "external_user_id": kwargs.get("external_user_id", "vishnu"),
        "app_slug": kwargs.get("app_slug", "asana"),
        "server_url": kwargs.get("server_url", "https://remote.mcp.pipedream.net"),
        "access_token": kwargs.get("access_token"),  # Include access_token in config
    }
    
    return PipedreamMCPClient(**config)