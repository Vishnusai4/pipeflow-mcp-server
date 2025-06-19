from fastapi import APIRouter, Request, Query
from fastapi.responses import RedirectResponse
from typing import Optional
from ..core.mcp_client import create_pipedream_client

# Initialize the MCP client
mcp_client = create_pipedream_client()

router = APIRouter()

@router.get("/auth/callback")
async def oauth_callback(
    request: Request,
    code: str = Query(..., description="OAuth authorization code"),
    state: str = Query(..., description="OAuth state parameter"),
    error: Optional[str] = Query(None, description="OAuth error, if any"),
    error_description: Optional[str] = Query(None, description="OAuth error description, if any")
):
    """
    Handle OAuth callback from the provider.
    This endpoint is called by the OAuth provider after the user has authenticated.
    """
    if error:
        # Handle OAuth error
        error_msg = f"OAuth error: {error}"
        if error_description:
            error_msg += f" - {error_description}"
        return RedirectResponse(
            url=f"/dashboard/apps?error={error_msg}", 
            status_code=303
        )
    
    try:
        # Exchange the authorization code for an access token
        # and store the token in the database
        result = await mcp_client.handle_oauth_callback(
            code=code,
            state=state,
            request=request
        )
        
        # Redirect back to the apps page with a success message
        return RedirectResponse(
            url=f"/dashboard/apps?success=1&app={result.get('app_slug', '')}",
            status_code=303
        )
        
    except Exception as e:
        # Log the error and redirect to the apps page with an error message
        print(f"Error in OAuth callback: {str(e)}")
        return RedirectResponse(
            url=f"/dashboard/apps?error={str(e)}",
            status_code=303
        )
