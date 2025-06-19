import os
import json
import secrets
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode, urljoin
import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.schema import OAuthState

from app.constants import [
    PIPEDREAM_CLIENT_ID,
    PIPEDREAM_CLIENT_SECRET,
    PIPEDREAM_PROJECT_ID,
    PIPEDREAM_ENVIRONMENT,
]
class PipedreamAuthService:
    def __init__(self):
        self.client_id = settings.PIPEDREAM_CLIENT_ID
        self.client_secret = settings.PIPEDREAM_CLIENT_SECRET
        self.redirect_uri = f"{settings.APP_URL}/auth/callback"
        self.base_url = "https://api.pipedream.com/oauth/authorize"
        self.token_url = "https://api.pipedream.com/oauth/access_token"

    async def generate_auth_url(
        self, 
        app_slug: str,
        user_id: str,
        scopes: list[str] = None,
        state_data: dict = None
    ) -> str:
        """Generate OAuth URL with state containing app and user context"""
        if not scopes:
            scopes = ["basic"]
            
        # Generate a secure state token
        state_token = secrets.token_urlsafe(32)
        
        # Store state with user and app context
        state = OAuthState(
            token=state_token,
            user_id=user_id,
            app_slug=app_slug,
            scopes=scopes,
            data=state_data or {}
        )
        
        # In a production app, you'd store this in a secure session or cache
        # with a short TTL
        # await cache.set(f"oauth_state:{state_token}", state.json(), ex=300)
        
        # Build the OAuth URL
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state_token,
        }
        
        return f"{self.base_url}?{urlencode(params)}"

    async def exchange_code_for_token(
        self, 
        code: str, 
        state_token: str
    ) -> Tuple[Dict, OAuthState]:
        """Exchange authorization code for access token and validate state"""
        # In production, retrieve and validate the state from your cache
        # state_data = await cache.get(f"oauth_state:{state_token}")
        # if not state_data:
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail="Invalid or expired state token"
        #     )
        # state = OAuthState.parse_raw(state_data)
        
        # For now, we'll just validate the format
        if not state_token or len(state_token) < 10:  # Basic validation
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid state token"
            )
            
        # Exchange code for token
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.token_url, data=data)
                response.raise_for_status()
                token_data = response.json()
                
                # In a real implementation, you'd want to store the token securely
                # and associate it with the user and app
                return token_data, None  # Replace None with actual state when implemented
                
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to exchange code for token: {str(e)}"
                )

    async def create_sign_in_link(
        self,
        app_slug: str,
        user_id: str,
        scopes: list[str] = None,
        return_url: str = None
    ) -> str:
        """Create a sign-in link for the specified app"""
        # Generate an OAuth URL with the necessary parameters
        auth_url = await self.generate_auth_url(
            app_slug=app_slug,
            user_id=user_id,
            scopes=scopes,
            state_data={"return_url": return_url} if return_url else None
        )
        
        # In a real implementation, you might want to:
        # 1. Create a short-lived, one-time-use token
        # 2. Store the auth URL with this token in a secure cache
        # 3. Return a link to your frontend that uses this token
        # 4. The frontend would then redirect to the actual OAuth URL
        
        # For now, we'll return the direct OAuth URL
        return auth_url

# Singleton instance
pipedream_auth = PipedreamAuthService()
