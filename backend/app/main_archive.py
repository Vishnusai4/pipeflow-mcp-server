# Corrected main.py for New MCP Client
"""
FastAPI backend for AI agent system with MCP integration
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional, Any
import uvicorn
from datetime import datetime, timedelta
import jwt
import uuid
import os
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
    title="AI Agent MCP backend",
    description="Backend API for MCP server integrating with 30+ apps via MCP",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TB configured for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=['*'],
)

# Security
security = HTTPBearer()

# Initialize session store
session_store = SessionStore()  # Fixed typo: was sesson_store

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return username"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


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
async def login(login_request: LoginRequest):
    """Authenticate user and return JWT token"""
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

    return LoginResponse(
        access_token=access_token,
        token_type='bearer',
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.get("/apps", response_model=List[AppInfo])
async def get_apps(current_user: str = Depends(verify_token)):
    """Get list of all MCP-enabled apps"""
    apps = []
    for app_name in MCP_APPS:
        app_slug = app_name.lower().replace(' ', '_').replace('.', '')
        apps.append(AppInfo(
            name=app_name,
            slug=app_slug,
            description=f"Integration with {app_name}",
            category=_get_app_category(app_name),  # Fixed: added missing comma
            is_connected=session_store.has_session(current_user, app_slug)
        ))

    return apps


@app.post("/connect_app", response_model=ConnectAppResponse)
async def connect_app(
    request: ConnectAppRequest,
    current_user: str = Depends(verify_token)
):
    """Connect to an MCP-enabled app and initialize session"""
    app_slug = request.app_slug

    # Validate app exists
    app_names = [name.lower().replace(' ', '_').replace('.', '') for name in MCP_APPS]
    if app_slug not in app_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"App '{app_slug}' is not supported"
        )
    
    try:
        # Create MCP client with your new configuration
        mcp_client = create_pipedream_client(
            client_id=PIPEDREAM_CLIENT_ID,
            client_secret=PIPEDREAM_CLIENT_SECRET,
            project_id=PIPEDREAM_PROJECT_ID,
            environment=PIPEDREAM_ENVIRONMENT,
            external_user_id=current_user,
            app_slug=app_slug
        )

        # Initialize session using your new client
        session_result = mcp_client.initialize_session()
        
        # Check if initialization was successful
        if session_result.get("status_code") not in [200, 201]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize session: {session_result.get('response', 'Unknown error')}"
            )

        # Generate session ID for our internal tracking
        session_id = str(uuid.uuid4())

        # Get available tools using your new client
        tools_result = mcp_client.list_tools()
        tools = []
        
        if tools_result.get("status_code") in [200, 201]:
            # Parse tools from the response
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
    current_user: str = Depends(verify_token)
):
    """Get session info for LLM agent access"""
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
async def get_user_sessions(current_user: str = Depends(verify_token)):
    """Get all active sessions for current user"""
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
async def disconnect_app(app_slug: str, current_user: str = Depends(verify_token)):
    """Disconnect from an app and cleanup session"""
    success = session_store.remove_session(current_user, app_slug)  # Fixed typo: was sesson_store
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active session found for app {app_slug}"
        )
    
    return {"message": f"Successfully disconnected from {app_slug}"}


@app.post("/execute_tool/{session_id}", response_model = None)
async def execute_tool(
    session_id: str,
    tool_name: str,
    arguments: Dict[str, Any] = None,
    current_user: str = Depends(verify_token)
):
    """Execute a tool in a specific session"""
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
        result = mcp_client.call_tool(tool_name, arguments)
        
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
        "version": "1.0.0",
        "mcp_client": "pipedream-http-client"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
