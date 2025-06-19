from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from typing import Any
import logging

from app.core.security import get_current_user
from app.services.pipedream_auth import pipedream_auth
from app.models.schema import (
    SignInLinkRequest,
    SignInLinkResponse,
    OAuthCallbackRequest,
    OAuthTokenResponse,
    AppConnection,
    ConnectionStatus
)
from app.core.cache import cache  # You'll need to implement this

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/auth/signin-link", response_model=SignInLinkResponse)
async def create_sign_in_link(
    request: SignInLinkRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate a sign-in link for the specified app
    """
    try:
        # Generate the OAuth URL
        auth_url = await pipedream_auth.create_sign_in_link(
            app_slug=request.app_slug,
            user_id=current_user["sub"],
            scopes=request.scopes,
            return_url=request.return_url
        )
        
        # In a real implementation, you'd store this in a secure cache
        # with a short TTL
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        return SignInLinkResponse(
            url=auth_url,
            expires_at=expires_at
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create sign-in link: {str(e)}"
        )

@router.get("/auth/callback")
async def oauth_callback(
    code: str,
    state: str,
):
    """
    Handle OAuth callback from Pipedream
    """
    try:
        # Exchange the authorization code for an access token
        token_data, state_data = await pipedream_auth.exchange_code_for_token(code, state)
        
        # In a real implementation, you would:
        # 1. Validate the state token
        # 2. Store the access token securely
        # 3. Create/update the user's app connection
        # 4. Redirect to the return URL or a success page
        
        # For now, just return the token data
        return {
            "status": "success",
            "app_slug": state_data.app_slug if state_data else "unknown",
            "user_id": state_data.user_id if state_data else "unknown",
            "access_token": token_data.get("access_token"),
            "token_type": token_data.get("token_type"),
            "expires_in": token_data.get("expires_in"),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth callback failed: {str(e)}"
        )

@router.get("/auth/connections", response_model=list[AppConnection])
async def get_user_connections(
    current_user: dict = Depends(get_current_user),
):
    """
    Get all app connections for the current user
    """
    # In a real implementation, you would fetch this from your database
    # For now, return an empty list
    return []

@router.post("/auth/disconnect/{appSlug}")
async def disconnect_app(
    appSlug: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Disconnect an app for the current user
    """
    try:
        user_id = current_user["sub"]
        
        # Get the session store instance (you might need to import it)
        from app.store import session_store
        
        # Remove the session from the store
        session_removed = session_store.remove_session(user_id, appSlug)
        
        if not session_removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active session found for {appSlug}"
            )
            
        # In a production app, you might also want to:
        # 1. Revoke the access token with Pipedream
        # 2. Clean up any related data in your database
        
        return {"status": "success", "message": f"Successfully disconnected from {appSlug}"}
        
    except Exception as e:
        logger.error(f"Error disconnecting app {appSlug}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to disconnect from {appSlug}: {str(e)}"
        )
