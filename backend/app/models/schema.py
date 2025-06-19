#Pydantic models used for this applicaiton
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

#Authentication models
class LoginRequest(BaseModel):
    """Request model for user login"""
    username: str = Field(..., description = "Username for authentication")
    password: str = Field(..., description="Password for authentication")

class LoginResponse(BaseModel):
    """Response model for successful login"""
    access_token: str = Field(..., description="JWT access token")
    #token200: str = Field(default="bearer", description="Token type")
    token_type: str = Field(default='bearer', description = "Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    #user200: Optional[str] = Field(None, description="User identifier")
    user_id: Optional[str] = Field(None, description="User identifier")

#OAuth models
class OAuthState(BaseModel):
    """Model for OAuth state to maintain context during OAuth flow"""
    token: str
    user_id: str
    app_slug: str
    scopes: List[str] = ["basic"]
    data: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SignInLinkRequest(BaseModel):
    """Request model for generating a sign-in link"""
    app_slug: str
    scopes: List[str] = ["basic"]
    return_url: Optional[str] = None

class SignInLinkResponse(BaseModel):
    """Response model containing the sign-in link"""
    url: str
    expires_at: datetime

class OAuthCallbackRequest(BaseModel):
    """Request model for OAuth callback"""
    code: str
    state: str

class OAuthTokenResponse(BaseModel):
    """Response model for OAuth token exchange"""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    scope: str
    app_slug: str
    user_id: str

class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    PENDING = "pending"
    ERROR = "error"

class AppConnection(BaseModel):
    """Model representing a user's connection to an app"""
    app_slug: str
    status: ConnectionStatus
    scopes: List[str] = []
    connected_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    error: Optional[str] = None

#App Models
class AppInfo(BaseModel):
    """Model for app information"""
    name: str = Field(..., description="Display name of the app")
    slug: str = Field(..., description="URL-safe identifier of the app")
    description: str = Field(..., description="Brief description of the app")
    category: str = Field(..., description="Category of the app")
    is_connected: bool = Field(default=False, description="Whether user is connected to this app")
    tools_count: int = Field(default=0, description="Number of available tools")
    logo_url: str = Field(..., description="URL of the app's logo")

class ConnectAppRequest(BaseModel):
    app_slug: str = Field(..., description="Application slug to connect to")
    credentials: Optional[Dict[str,str]] = Field(None, description="Optional credentials for connection")

class ConnectAppResponse(BaseModel):
    success: bool = Field(..., description="Success status")
    session_id: Optional[str] = Field(None, description="Created session identifier")
    message: Optional[str] = Field(None, description="Connection status message")
    redirect_url: Optional[str] = Field(None, description="URL to redirect to after connection")
    connect_link: Optional[str] = Field(None, description="OAuth URL to open in popup")
    tools_count: Optional[int] = Field(0, description="Number of available tools")

# Session Models
class SessionInfo(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    app_slug: str = Field(..., description="Connected application slug")
    tools: List[Dict[str, Any]] = Field(default_factory=list, description="Available tools")
    created_at: datetime = Field(..., description="Session creation timestamp")
    is_active: bool = Field(default=True, description="Session active status")

class AgentSessionResponse(BaseModel):
    session_id: str = Field(..., description="Session identifer")
    user_id: str = Field(..., description="User identifer")
    app_slug: str = Field(..., description="Connected application slug")
    tools: List[Dict[str, Any]] = Field(default_factory=list, description="Available tools")
    is_active: bool = Field(default=True, description="Session active status")
    created_at: datetime = Field(..., description="Session creation timestamp")
    last_accessed: datetime = Field(..., description="Last access timestamp")
