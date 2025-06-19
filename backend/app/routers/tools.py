"""
Tool related routes.
"""
from fastapi import APIRouter, Depends

from ..core.security import require_authentication

router = APIRouter(prefix="/tools", tags=["tools"])

@router.get("/")
async def list_tools():
    """List all available tools."""
    return ["tool1", "tool2"]  # Placeholder
