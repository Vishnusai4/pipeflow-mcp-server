from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class AppInfo(BaseModel):
    slug: str
    name: str
    description: str
    category: str
    connected: bool = False
    tools_count: int = 0
    icon_url: Optional[str] = None

class ConnectAppRequest(BaseModel):
    all_slug: str
    credentials: Optional[Dict[str,str]] = None

class SessionInfo(BaseModel):
    session_id: str
    app_slug: str
    user_id: str
    status: str
    tools: List[Dict[str, Any]]
    connected_at: str
    metadata: Dict[str, Any] = {}

class HealthResponse(BaseModel):
    status: str
    version: str
    mcp_proxy_status: bool
    active_sessions: int

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None

class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]
    app_slug: Optional[str] = None

class ToolResult(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    app_slug: str
    tool_name: str