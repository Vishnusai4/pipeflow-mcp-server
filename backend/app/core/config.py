"""
Application configuration settings.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application settings
    PROJECT_NAME: str = "Pipeflow MCP Server"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]
    
    # Database (if needed)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    
    # Pipedream settings
    PIPEDREAM_API_KEY: Optional[str] = os.getenv("PIPEDREAM_API_KEY")
    PIPEDREAM_CLIENT_ID: Optional[str] = os.getenv("PIPEDREAM_CLIENT_ID")
    PIPEDREAM_CLIENT_SECRET: Optional[str] = os.getenv("PIPEDREAM_CLIENT_SECRET")
    PIPEDREAM_PROJECT_ID: Optional[str] = os.getenv("PIPEDREAM_PROJECT_ID")
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
