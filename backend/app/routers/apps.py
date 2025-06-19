"""
App related routes.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from ..core.mcp_client import PipedreamMCPClient as MCPClient
from ..core.security import require_authentication

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/apps", tags=["apps"])

@router.get("/")
async def list_apps(_: str = Depends(require_authentication)):
    """
    List all available apps with their connection status for the current user.
    
    Returns:
        dict: A dictionary containing the user ID and list of available apps with metadata
    """
    try:
        # Initialize MCP client with default values
        mcp_client = MCPClient(
            client_id="",  # These should come from your config
            client_secret="",
            project_id=""
        )
        
        # Get available apps from MCP
        available_apps = await mcp_client.get_available_apps()
        
        # Transform to the expected format
        return {
            "user": "current_user_id",  # This should be replaced with actual user ID from auth
            "apps": available_apps or []
        }
        
    except Exception as e:
        logger.error("Error fetching apps: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch apps: {str(e)}"
        )
