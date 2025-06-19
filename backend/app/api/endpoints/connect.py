"""
Connect app endpoint for handling OAuth connections.
"""
import logging
import uuid

from fastapi import Depends, HTTPException, status, Request

from ...core.mcp_client import create_pipedream_client
from ...models.schema import ConnectAppRequest, ConnectAppResponse
from ...core.security import require_authentication

logger = logging.getLogger(__name__)

async def connect_app(
    request: ConnectAppRequest,
    Cookie: Request,
    current_user: str = Depends(require_authentication)
) -> ConnectAppResponse:
    """
    Generate an OAuth sign-in link for the specified app
    Automatically authenticated via cookie
    """
    # Debug logging
    logger.info(f"Connect app request received for: {request.app_slug}")
    logger.info(f"Current user from auth: {current_user}")
    
    from ...main import (
        PIPEDREAM_CLIENT_ID,
        PIPEDREAM_CLIENT_SECRET,
        PIPEDREAM_PROJECT_ID,
        PIPEDREAM_ENVIRONMENT,
        get_access_token_for_api
    )
    
    app_slug = request.app_slug
    access_token = get_access_token_for_api(
        client_id=PIPEDREAM_CLIENT_ID,
        client_secret=PIPEDREAM_CLIENT_SECRET
    )
    
    # Debug log all cookies
    all_cookies = Cookie.cookies
    logger.info(f"All cookies: {all_cookies}")
    logger.info(f"Access token from cookies: {'present' if access_token else 'missing'}")
    if access_token:
        logger.info(f"Access token length: {len(access_token)}")
        logger.info(f"Access token starts with: {access_token[:10]}..." if access_token else "No token")

    # Validate app exists - import at function level to avoid circular imports
    from ...main import MCP_APPS
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
            state=f"{current_user}:{str(uuid.uuid4())}"  # Include a unique state parameter
        )

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
