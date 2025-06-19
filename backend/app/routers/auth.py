"""
Authentication routes for the application.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Any

from ..core.security import create_access_token, create_refresh_token
from ..schemas.token import Token
from ..schemas.user import UserInDB, User
from ..core.config import settings

router = APIRouter(tags=["auth"])

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    # This is a simplified example - in a real app, you would validate the credentials
    # against your user database
    if form_data.username != "test" or form_data.password != "test":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # In a real app, you would get the user from your database
    user = UserInDB(
        username=form_data.username,
        email=f"{form_data.username}@example.com",
        full_name="Test User",
        disabled=False,
        hashed_password="fakehashedpassword"  # In a real app, you would verify the password hash
    )
    
    # Create tokens
    access_token = create_access_token(subject=user.username)
    refresh_token = create_refresh_token(subject=user.username)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token
    }

@router.post("/refresh-token", response_model=Token)
async def refresh_token(refresh_token: str) -> Any:
    """
    Refresh an access token using a refresh token.
    """
    # In a real app, you would validate the refresh token
    # and issue a new access token
    return {
        "access_token": "new_access_token_here",
        "token_type": "bearer",
        "refresh_token": refresh_token
    }
