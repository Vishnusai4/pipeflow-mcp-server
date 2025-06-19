# Automatic Authentication FastAPI Backend with Cookie-based Session Management

"""
FastAPI backend for AI agent system with MCP integration
Uses automatic cookie-based authentication instead of manual JWT headers
"""

import json
import logging
import os
import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Awaitable, Callable, Dict, Optional

import httpx
import requests
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError
from .services.utils import read_app_info

# Import your constants and models
#from .api import connect_app
from .constants import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    MCP_APPS,
    PIPEDREAM_CLIENT_ID,
    PIPEDREAM_CLIENT_SECRET,
    PIPEDREAM_ENVIRONMENT,
    PIPEDREAM_PROJECT_ID,
    REFRESH_SECRET_KEY,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
    USERS,
)
from .core.mcp_client import create_pipedream_client
from .core.utils import read_app_info
from .models.schema import (
    AgentSessionResponse,
    ConnectAppRequest,
    ConnectAppResponse,
    LoginRequest,
    LoginResponse,
)
from .routers import apps, auth, oauth, sessions, tools, users
from .store import SessionStore

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see all logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
# Set specific log levels if needed
# logging.getLogger('httpx').setLevel(logging.WARNING)
# logging.getLogger('httpcore').setLevel(logging.WARNING)

app = FastAPI(
    title="AI Agent MCP backend with Automatic Authentication",
    description="Backend API for MCP server integrating with 30+ apps via MCP with automatic cookie-based auth",
    version="2.0.0"
)

# Add middleware to handle OPTIONS requests
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response
    
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# CORS middleware configuration
# For development, you might want to allow all origins
# In production, specify exact origins
cors_origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",  # Common Vite dev server port
    "http://127.0.0.1:5173",
    "http://localhost:3001",  # Common alternative frontend port
]

# Add CORS middleware with proper configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,  # Important for cookies
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
    max_age=86400,  # 24 hours for preflight cache
)

# --- Minimal Authenticated Endpoints for Debugging ---
from fastapi import APIRouter
router = APIRouter()


# Initialize session store
session_store = SessionStore()

# Cache for Pipedream apps
pipedream_apps_cache = {"data": [], "has_more": False, "page": 0, "total": 0}
pipedream_apps_last_fetched = None
CACHE_DURATION = 3600  # 1 hour in seconds

async def get_pipedream_apps() -> Dict[str, Any]:
    """Fetch apps from Pipedream API with caching"""
    global pipedream_apps_cache, pipedream_apps_last_fetched
    
    # Return cached data if it's still fresh
    if pipedream_apps_last_fetched and (datetime.utcnow() - pipedream_apps_last_fetched).total_seconds() < CACHE_DURATION:
        logger.debug("Returning cached Pipedream apps")
        return pipedream_apps_cache
    
    try:
        if not PIPEDREAM_CLIENT_SECRET:
            raise ValueError("PIPEDREAM_CLIENT_SECRET not configured")
            
        url = "https://api.pipedream.com/v1/apps"
        headers = {
            "Authorization": f"Bearer {PIPEDREAM_CLIENT_SECRET}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Fetching apps from Pipedream API")
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, dict) or 'data' not in data:
                raise ValueError("Invalid Pipedream API response format")
                
            logger.info("Received %d apps from Pipedream API", len(data['data']))
            if data['data']:
                logger.debug("Sample app data: %s", json.dumps(data['data'][0], indent=2))
            
            # Cache the results
            pipedream_apps_cache = data
            pipedream_apps_last_fetched = datetime.utcnow()
            return data
            
    except Exception as e:
        logger.error(f"Error fetching Pipedream apps: {str(e)}", exc_info=True)
        # Return cached data even if it's stale if available
        if pipedream_apps_cache:
            logger.warning("Returning stale cached data due to API error")
        return pipedream_apps_cache if pipedream_apps_cache else {"data": [], "has_more": False, "page": 0, "total": 0}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a new access token"""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if not expires_delta:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = now + expires_delta
    
    logger.debug(f"Creating access token with expiration: {expire} (UTC)")
    
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.debug(f"Created access token expiring at {expire} (UTC)")
    return encoded_jwt

def get_access_token_for_api(client_id: str, client_secret: str) -> str:
    """Create access token for API clinet"""
    authenticate_url = "https://api.pipedream.com/v1/oauth/token"
    try:
        token_resp = requests.post(authenticate_url,
        json={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        })
        token_resp.raise_for_status()
        return token_resp.json().get("access_token")
    except Exception as e:
        logger.error(f"Failed to authenticate for API: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to authenticate for API: {str(e)}"
        )

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a new refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    return jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str, is_refresh: bool = False) -> dict:
    """Verify JWT token and return payload if valid"""
    try:
        secret_key = REFRESH_SECRET_KEY if is_refresh else SECRET_KEY
        logger.debug(f"Verifying {'refresh' if is_refresh else 'access'} token")
        
        # First, decode without verification to get the expiration time
        unverified_payload = jwt.get_unverified_claims(token)
        exp = unverified_payload.get('exp')
        if exp:
            exp_time = datetime.fromtimestamp(exp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            logger.debug(f"Token exp: {exp_time} (UTC), Current time: {now} (UTC)")
            if now > exp_time:
                logger.error(f"❌ Token expired at {exp_time} (UTC), current time: {now} (UTC)")
                raise jwt.ExpiredSignatureError("Token has expired")
        
        # Now verify the token
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_exp": True}
        )
        logger.debug("✅ Token verified successfully")
        return payload
        
    except jwt.ExpiredSignatureError as e:
        logger.error(f"❌ Token has expired: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"❌ Invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"❌ Token verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

async def get_current_user_from_request(request: Request) -> Optional[str]:
    """
    Extract user from request - checks cookies, Authorization header, and query params
    This provides automatic authentication without requiring manual token passing
    """
    logger.debug("\n=== AUTHENTICATION CHECK START ===")
    logger.debug(f"Request URL: {request.method} {request.url}")
    logger.debug(f"All request cookies: {request.cookies}")
    logger.debug(f"All request headers: {dict(request.headers)}")
    logger.debug(f"Query params: {dict(request.query_params)}")
    
    access_token = None
    token_source = None
    
    # 1. Try to get token from cookie (for browser-based auth)
    if "access_token" in request.cookies:
        access_token = request.cookies.get("access_token")
        token_source = "cookie"
        logger.debug("✅ Access token found in cookies.")
    
    # 2. Try Authorization header (for API clients)
    if not access_token:
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            access_token = authorization.split(" ", 1)[1]
            token_source = "header"
            logger.debug("✅ Access token found in Authorization header.")
    
    # 3. Try query parameter (for development/debugging only)
    if not access_token and "access_token" in request.query_params:
        access_token = request.query_params.get("access_token")
        token_source = "query_param"
        logger.warning("⚠️ Access token provided via query parameter (development only).")
    
    if not access_token:
        logger.error("❌ No access token found in request (checked cookies, headers, and query params)")
        logger.debug("=== AUTHENTICATION CHECK FAILED - NO TOKEN ===\n")
        return None
    
    logger.debug(f"🔑 Access token source: {token_source}")
    logger.debug(f"🔑 Access token (first 10 chars): {access_token[:10]}...")
    
    try:
        # Verify the token
        logger.debug("🔍 Verifying token...")
        payload = verify_token(access_token)
        username: str = payload.get("sub")
        
        if not username:
            logger.error("❌ No 'sub' claim found in token payload")
            return None
            
        # Check token expiration
        exp = payload.get('exp')
        if exp:
            from datetime import datetime
            exp_time = datetime.fromtimestamp(exp)
            logger.debug(f"⏱️ Token expires at: {exp_time} (UTC)")
            if datetime.utcnow() > exp_time:
                logger.error("❌ Token has expired!")
                return None
        
        logger.info(f"✅ Successfully authenticated user: {username}")
        logger.debug(f"🔑 Token payload: { {k: v for k, v in payload.items() if k != 'exp'} }")
        logger.debug("=== AUTHENTICATION CHECK SUCCESS ===\n")
        return username
        
    except ExpiredSignatureError:
        logger.error("❌ Token has expired")
    except JWTError as e:
        logger.error(f"❌ Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Unexpected error during token verification: {str(e)}")
    
    logger.debug("=== AUTHENTICATION CHECK FAILED - INVALID TOKEN ===\n")
    return None


async def require_authentication(request: Request) -> str:
    """
    Dependency that requires authentication
    Automatically checks cookies and headers
    """
    logger.debug(f"Authentication required for: {request.method} {request.url}")
    logger.debug(f"Request headers: {dict(request.headers)}")
    logger.debug(f"Request cookies: {request.cookies}")
    current_user = await get_current_user_from_request(request)
    if not current_user:
        logger.warning("Authentication failed: No valid authentication token found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Not authenticated. Please log in. "
                "Hint: Make sure your client is sending the 'access_token' cookie or an 'Authorization: Bearer <token>' header. "
                "For debugging, call /auth/debug to see exactly what cookies and headers the backend is receiving."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

# --- Minimal Authenticated Endpoints for Debugging ---
@app.get("/user/sessions")
async def get_user_sessions(current_user: str = Depends(require_authentication)):
    """Return dummy user session info if authenticated."""
    return {"user": current_user, "sessions": ["session1", "session2"]}

@app.get("/apps")
async def get_apps(current_user: str = Depends(require_authentication)):
    """Return the list of supported apps."""
    # Return just the list of apps to match frontend expectations
    return read_app_info()

@app.get("/auth/debug")
async def auth_debug(request: Request):
    """
    Returns cookies, headers, and extracted access token for debugging client/backend auth communication.
    """
    access_token = None
    token_source = None
    if "access_token" in request.cookies:
        access_token = request.cookies.get("access_token")
        token_source = "cookie"
    authorization = request.headers.get("Authorization")
    if not access_token and authorization and authorization.startswith("Bearer "):
        access_token = authorization.split(" ", 1)[1]
        token_source = "header"
    return {
        "cookies": dict(request.cookies),
        "headers": dict(request.headers),
        "access_token_first_10": access_token[:10] + "..." if access_token else None,
        "token_source": token_source,
        "authorization_header": authorization,
    }

def _get_app_category(app_name: str) -> str:
    """
    Get the category for an app from app_info.json.
    Returns the first category if found, otherwise 'Other'.
    Always returns a string.
    """
    if not app_name or not isinstance(app_name, str):
        return "Other"
        
    try:
        # Import read_app_info locally to avoid circular imports
        from app.services.utils import read_app_info
        
        # Find the app in app_info.json
        for app in read_app_info():
            if not isinstance(app, dict):
                continue
                
            if app.get('name') == app_name and 'app_category' in app and app['app_category']:
                # Handle case where app_category is a list
                if isinstance(app['app_category'], list) and len(app['app_category']) > 0:
                    category = app['app_category'][0]
                else:
                    category = app['app_category']
                
                # Ensure we return a string
                return str(category) if category is not None else "Other"
                
        return "Other"
    except Exception as e:
        print(f"Error getting app category for {app_name}: {e}")
        return "Other"

# Include all routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(apps.router, prefix="/api/apps", tags=["apps"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])
app.include_router(oauth.router, prefix="/api/oauth", tags=["oauth"])

# Register the connect_app route directly with the app
#app.add_api_route("/connect_app", connect_app, methods=["POST"], response_model=ConnectAppResponse)

@app.get("/")
def root():
    return {"message": "Welcome to the app!"}

@app.get("/test-log")
def test_log():
    logger.info("Testing the logging feature")

@app.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest, response: Response):
    """
    Authenticate user and set secure cookies for automatic authentication
    Sets both access and refresh tokens as HTTP-only cookies
    """
    logger.info(f"Login attempt for user: {login_request.username}")
    
    # Verify user credentials
    stored_password = USERS.get(login_request.username)
    if not stored_password or stored_password != login_request.password:
        logger.warning(f"❌ Failed login attempt for user: {login_request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": login_request.username}, 
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": login_request.username}, 
        expires_delta=refresh_token_expires
    )

    # Set cookie attributes
    cookie_args = {
        "httponly": True,
        "secure": False,  # Set to True in production with HTTPS
        "samesite": "lax",
        "path": "/",
        "domain": "localhost",  # Explicitly set domain for local development
    }

    # Log cookie settings for debugging
    logger.info(f"Setting cookies with domain: {cookie_args['domain']}")
    
    # Set access token cookie (short-lived)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=access_token_expires.seconds,
        **cookie_args
    )
    
    # Set refresh token cookie (long-lived)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=refresh_token_expires.days * 24 * 3600,
        **cookie_args
    )
    
    # Log successful login
    logger.info(f"✅ User {login_request.username} logged in successfully")
    logger.debug(f"Access token (first 10 chars): {access_token[:10]}...")
    logger.debug(f"Refresh token (first 10 chars): {refresh_token[:10]}...")
    
    # Return tokens in response body (for clients that need them)
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type='bearer',
        expires_in=access_token_expires.seconds,
        user_id=login_request.username
    )

@app.get("/me")
async def get_current_user(request: Request):
    """Get current user info"""
    # Get the token from the Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return {"user_id": username, "username": username, "email": f"{username}@example.com"}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

@app.post("/logout")
async def logout(response: Response):
    """Logout user by clearing the authentication cookie"""
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Successfully logged out"}


@app.post("/refresh")
async def refresh_token(request: Request, response: Response):
    """Refresh access token using refresh token"""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing"
        )
    
    try:
        # Verify refresh token
        payload = verify_token(refresh_token, is_refresh=True)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Create new access token
        access_token_expires = timedelta(minutes=15)
        new_access_token = create_access_token(
            data={"sub": username},
            expires_delta=access_token_expires
        )
        
        # Set new access token in cookie
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            max_age=access_token_expires.seconds,
            httponly=True,
            secure=False,
            samesite="lax"
        )
        
        return {"access_token": new_access_token, "token_type": "bearer"}
        
    except JWTError as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

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


@app.post("/connect_app", response_model=ConnectAppResponse)
async def connect_app(
    connect_request: ConnectAppRequest,
    request: Request,
    current_user: str = Depends(require_authentication)
):
    """
    Generate an OAuth sign-in link for the specified app
    Automatically authenticated via cookie
    """
    # Debug logging
    logger.info("=== CONNECT_APP REQUEST START ===")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request cookies: {request.cookies}")
    logger.info(f"Current user from auth: {current_user}")
    
    # Get app_slug from the request body
    app_slug = connect_request.app_slug
    logger.info(f"Connect app request received for app_slug: {app_slug}")
    
    if not app_slug:
        logger.error("No app_slug provided in the request")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="app_slug is required"
        )
    
    # Log the full request body for debugging
    try:
        body = await request.body()
        logger.debug(f"Request body: {body.decode()}")
    except Exception as e:
        logger.warning(f"Could not log request body: {e}")
    
    # Get API access token
    access_token = get_access_token_for_api(
        client_id=PIPEDREAM_CLIENT_ID,
        client_secret=PIPEDREAM_CLIENT_SECRET
    )
    
    logger.info(f"API access token: {'present' if access_token else 'missing'}")
    if access_token:
        logger.info(f"API access token length: {len(access_token)}")
        logger.info(f"API access token starts with: {access_token[:10]}..." if access_token else "No token")

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
            app_slug=app_slug,
            access_token=access_token
        )

        # Generate OAuth sign-in link
        connect_link = await mcp_client.initialize_connection(
            user_id=current_user,
            project_id=PIPEDREAM_PROJECT_ID,
            app_slug=app_slug
        )

        logger.info("Connection link: " + str(connect_link))

        if not connect_link:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate sign-in link"
            )

        return ConnectAppResponse(
            success=True,
            session_id=None,  # No session ID yet
            message=f"Click the button to authenticate with {app_slug}",
            redirect_url="/dashboard/apps",  # Where to redirect after success
            connect_link=connect_link,  # The OAuth URL to open in popup
            tools_count=0
        )

    except Exception as e:
        logger.error(f"Failed to connect to {app_slug}: {str(e)}")
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



@app.get("/apps")
async def get_filtered_apps(authentication: str = Depends(require_authentication)):
    """Get filtered list of apps from Pipedream that are in MCP_APPS"""
    try:
        # Get all apps from Pipedream
        app_info = read_app_info()
        logger.info(f"Returning {len(app_info)} filtered apps")
        return {"apps": app_info}
            
    except requests.exceptions.HTTPError as http_err:
        error_msg = f"HTTP error occurred: {http_err}"
        if hasattr(http_err, 'response') and hasattr(http_err.response, 'text'):
            error_msg += f"\nResponse text: {http_err.response.text}"
        logger.error(error_msg)
    except Exception as err:
        logger.error(f"Other error occurred: {err}")


# Middleware to automatically clean up expired sessions
@app.middleware("http")
async def cleanup_expired_sessions_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Middleware to periodically clean up expired sessions.
    
    Args:
        request: The incoming request
        call_next: Next middleware or request handler
        
    Returns:
        Response: The response from the next middleware/handler
    """
    # Call the next middleware/request handler and get the response
    response = await call_next(request)
    
    # Clean up expired sessions every 100 requests (approximately)
    if random.randint(1, 100) == 1:  # nosec - not used for security
        try:
            session_store.cleanup_expired_sessions()
        except Exception as e:
            # Log error but don't fail the request
            logger.error("Error cleaning up sessions: %s", str(e))
    
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)