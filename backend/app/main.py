# Automatic Authentication FastAPI Backend with Cookie-based Session Management

"""
FastAPI backend for AI agent system with MCP integration
Uses automatic cookie-based authentication instead of manual JWT headers
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request, Response, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional, Any
import uvicorn
from datetime import datetime, timedelta
import jwt
import uuid
import os

# Import your constants and models
from constants import (
    MCP_APPS,
    USERS,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    PIPEDREAM_CLIENT_ID,
    PIPEDREAM_CLIENT_SECRET,
    PIPEDREAM_PROJECT_ID,
    PIPEDREAM_ENVIRONMENT,
)

from models.schema import (
    LoginRequest,
    LoginResponse,
    AppInfo,
    ConnectAppRequest,
    ConnectAppResponse,
    SessionInfo,
    AgentSessionResponse
)

from store import SessionStore
from core.mcp_client import create_pipedream_client

app = FastAPI(
    title="AI Agent MCP backend with Automatic Authentication",
    description="Backend API for MCP server integrating with 30+ apps via MCP with automatic cookie-based auth",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,  # Important: Allow cookies
    allow_methods=["*"],
    allow_headers=['*'],
)

# Initialize session store
session_store = SessionStore()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user_from_request(request: Request) -> Optional[str]:
    """
    Extract user from request - checks both cookies and Authorization header
    This provides automatic authentication without requiring manual token passing
    """
    # First, try to get token from cookie (automatic authentication)
    access_token = request.cookies.get("access_token")
    
    # If no cookie, try Authorization header (fallback for API clients)
    if not access_token:
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            access_token = authorization.split(" ")[1]
    
    if not access_token:
        return None
    
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        return username
    except jwt.PyJWTError:
        return None

async def require_authentication(request: Request) -> str:
    """
    Dependency that requires authentication
    Automatically checks cookies and headers
    """
    current_user = await get_current_user_from_request(request)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

def _get_app_category(app_name: str) -> str:
    """Categorize apps for better organization"""
    dev_tools = ['GitHub', 'GitLab', 'Bitbucket', 'Azure DevOps', 'Jenkins', 'CircleCI', 'GitHub Actions']
    cloud_platforms = ['Amazon Web Services', 'Google Cloud Platform', 'Microsoft Azure', 'DigitalOcean']
    monitoring = ['Grafana', 'Prometheus', 'Datadog', 'New Relic', 'Logz.io', 'Sentry']
    communication = ['Slack', 'Microsoft Teams', 'Discord']
    project_mgmt = ['Jira', 'Asana', 'Linear', 'Notion']
    support = ['Zendesk', 'Intercom']
    security = ['Snyk', 'SonarQube']
    databases = ['MongoDB Atlas', 'Redis Enterprise']
    testing = ['Postman', 'Cypress']
    
    if app_name in dev_tools:
        return "Development"
    elif app_name in cloud_platforms:
        return "Cloud Platform"
    elif app_name in monitoring:
        return "Monitoring"
    elif app_name in communication:
        return "Communication"
    elif app_name in project_mgmt:
        return "Project Management"
    elif app_name in support:
        return "Customer Support"
    elif app_name in security:
        return "Security"
    elif app_name in databases:
        return "Database"
    elif app_name in testing:
        return "Testing"
    else:
        return "Other"

@app.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest, response: Response):
    """
    Authenticate user and set secure cookie for automatic authentication
    No need to manually send tokens after this!
    """
    username = login_request.username
    password = login_request.password

    if username not in USERS or USERS[username] != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )

    # Set secure, HTTP-only cookie for automatic authentication
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Cookie expires with token
        httponly=True,  # Cannot be accessed by JavaScript (security)
        secure=False,   # Set to True in production with HTTPS
        samesite="lax", # CSRF protection
        path="/"        # Available for all paths
    )

    return LoginResponse(
        access_token=access_token,
        token_type='bearer',
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=username
    )

@app.post("/logout")
async def logout(response: Response):
    """Logout user by clearing the authentication cookie"""
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Successfully logged out"}

@app.get("/me")
async def get_current_user_info(request: Request):
    """Get current user info - demonstrates automatic authentication"""
    current_user = await get_current_user_from_request(request)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return {
        "username": current_user,
        "authenticated": True,
        "login_time": datetime.utcnow().isoformat()
    }

@app.get("/apps", response_model=List[AppInfo])
async def get_apps(current_user: str = Depends(require_authentication)):
    """
    Get list of all MCP-enabled apps
    Automatically authenticated via cookie - no manual token needed!
    """
    apps = []
    for app_name in MCP_APPS:
        app_slug = app_name.lower().replace(' ', '_').replace('.', '')
        apps.append(AppInfo(
            name=app_name,
            slug=app_slug,
            description=f"Integration with {app_name}",
            category=_get_app_category(app_name),
            is_connected=session_store.has_session(current_user, app_slug),
            tools_count=0  # Will be updated when connected
        ))
    return apps

@app.post("/connect_app", response_model=ConnectAppResponse)
async def connect_app(
    request: ConnectAppRequest,
    current_user: str = Depends(require_authentication)
):
    """
    Connect to an MCP-enabled app and initialize session
    Automatically authenticated via cookie
    """
    app_slug = request.app_slug

    # Validate app exists
    app_names = [name.lower().replace(' ', '_').replace('.', '') for name in MCP_APPS]
    if app_slug not in app_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"App '{app_slug}' is not supported"
        )

    try:
        # Create MCP client with your configuration
        mcp_client = create_pipedream_client(
            client_id=PIPEDREAM_CLIENT_ID,
            client_secret=PIPEDREAM_CLIENT_SECRET,
            project_id=PIPEDREAM_PROJECT_ID,
            environment=PIPEDREAM_ENVIRONMENT,
            external_user_id=current_user,
            app_slug=app_slug
        )

        # Initialize session using your client
        session_result = mcp_client.initialize_session()

        # Check if initialization was successful
        if session_result.get("status_code") not in [200, 201]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize session: {session_result.get('response', 'Unknown error')}"
            )

        # Generate session ID for internal tracking
        session_id = str(uuid.uuid4())

        # Get available tools
        tools_result = mcp_client.list_tools()
        tools = []
        if tools_result.get("status_code") in [200, 201]:
            response_data = tools_result.get("response", {})
            if isinstance(response_data, dict) and "result" in response_data:
                tools = response_data["result"].get("tools", [])
            elif isinstance(response_data, dict) and "tools" in response_data:
                tools = response_data["tools"]

        # Store session info
        session_info = {
            "session_id": session_id,
            "user_id": current_user,
            "app_slug": app_slug,
            "tools": tools,
            "created_at": datetime.utcnow().isoformat(),
            "is_active": True,
            "mcp_response": session_result.get("response"),
            "client_config": {
                "external_user_id": current_user,
                "app_slug": app_slug,
                "environment": PIPEDREAM_ENVIRONMENT
            }
        }

        session_store.store_session(current_user, app_slug, session_info)

        return ConnectAppResponse(
            success=True,
            session_id=session_id,
            message=f"Successfully connected to {app_slug}",
            tools_count=len(tools)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to {app_slug}: {str(e)}"
        )

@app.get("/agent/session/{user_id}/{app_slug}", response_model=AgentSessionResponse)
async def get_agent_session(
    user_id: str,
    app_slug: str,
    current_user: str = Depends(require_authentication)
):
    """
    Get session info for LLM agent access
    Automatically authenticated via cookie
    """
    # Verify user has permission to access this session
    if current_user != user_id and current_user != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this session"
        )

    session_info = session_store.get_session(user_id, app_slug)
    if not session_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active session found for user {user_id} and app {app_slug}"
        )

    return AgentSessionResponse(
        session_id=session_info["session_id"],
        user_id=session_info["user_id"],
        app_slug=session_info["app_slug"],
        tools=session_info.get("tools", []),
        is_active=session_info.get("is_active", True),
        created_at=session_info.get("created_at"),
        last_accessed=datetime.utcnow()
    )

@app.get("/user/sessions")
async def get_user_sessions(current_user: str = Depends(require_authentication)):
    """
    Get all active sessions for current user
    Automatically authenticated via cookie
    """
    sessions = session_store.get_user_sessions(current_user)
    return {
        "user_id": current_user,
        "sessions": [
            {
                "app_slug": session.get("app_slug"),
                "session_id": session.get("session_id"),
                "created_at": session.get("created_at"),
                "is_active": session.get("is_active", True),
                "tools_count": len(session.get("tools", []))
            } for session in sessions
        ]
    }

@app.delete("/disconnect_app/{app_slug}")
async def disconnect_app(
    app_slug: str, 
    current_user: str = Depends(require_authentication)
):
    """
    Disconnect from an app and cleanup session
    Automatically authenticated via cookie
    """
    success = session_store.remove_session(current_user, app_slug)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active session found for app {app_slug}"
        )

    return {"message": f"Successfully disconnected from {app_slug}"}

@app.post("/execute_tool/{session_id}", response_model=None)
async def execute_tool(
    session_id: str,
    tool_name: str,
    arguments: Dict[str, Any] = None,
    current_user: str = Depends(require_authentication)
):
    """
    Execute a tool in a specific session
    Automatically authenticated via cookie
    """
    # Find session by ID
    user_sessions = session_store.get_user_sessions(current_user)
    session_info = None
    
    for session in user_sessions:
        if session.get("session_id") == session_id:
            session_info = session
            break
    
    if not session_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    try:
        # Create client for this session
        client_config = session_info.get("client_config", {})
        mcp_client = create_pipedream_client(
            client_id=PIPEDREAM_CLIENT_ID,
            client_secret=PIPEDREAM_CLIENT_SECRET,
            project_id=PIPEDREAM_PROJECT_ID,
            environment=PIPEDREAM_ENVIRONMENT,
            external_user_id=client_config.get("external_user_id", current_user),
            app_slug=client_config.get("app_slug", session_info.get("app_slug"))
        )
        
        # Execute the tool
        result = mcp_client.call_tool(tool_name, arguments or {})
        
        return {
            "session_id": session_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "2.0.0",
        "mcp_client": "pipedream-http-client",
        "authentication": "automatic-cookie-based"
    }

# Middleware to automatically clean up expired sessions
@app.middleware("http")
async def cleanup_expired_sessions_middleware(request: Request, call_next):
    """Middleware to periodically clean up expired sessions"""
    response = await call_next(request)
    
    # Clean up expired sessions every 100 requests (approximately)
    import random
    if random.randint(1, 100) == 1:
        try:
            session_store.cleanup_expired_sessions()
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error cleaning up sessions: {e}")
    
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)