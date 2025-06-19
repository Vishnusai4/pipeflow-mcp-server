"""
Session related routes.
"""
from fastapi import APIRouter, Depends

from ..core.security import require_authentication

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.get("/")
async def list_sessions():
    """List all active sessions."""
    return ["session1", "session2"]  # Placeholder
