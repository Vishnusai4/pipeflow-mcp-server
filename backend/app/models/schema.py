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

#App Models
class AppInfo(BaseModel):
    """Model for app information"""
    name: str = Field(..., description="Display name of the app")
    slug: str = Field(..., description="URL-safe identifier of the app")
    description: str = Field(..., description="Brief description of the app")
    category: str = Field(..., description="Category of the app")
    is_connected: bool = Field(default=False, description="Whether user is connected to this app")
    tools_count: int = Field(default=0, description="Number of available tools")

class ConnectAppRequest(BaseModel):
    app_slug: str = Field(..., description="Application slug to connect to")
    credentials: Optional[Dict[str,str]] = Field(None, description="Optional credentials for connection")

class ConnectAppResponse(BaseModel):
    success: bool = Field(..., description="Success status")
    session_id: Optional[str] = Field(None, description="Created session identifier")
    message: Optional[str] = Field(None, description="Connection status message")
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



