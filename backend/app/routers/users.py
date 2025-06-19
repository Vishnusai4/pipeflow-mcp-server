"""
User related routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from .. import schemas
from ..core.security import require_authentication

router = APIRouter(prefix="/users", tags=["users"])

# In-memory user store for demo purposes
# In a real app, this would be a database
users_db = {}

@router.post("/", response_model=schemas.User)
async def create_user(user: schemas.UserCreate):
    """Create a new user."""
    if user.username in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # In a real app, you would hash the password here
    db_user = schemas.UserInDB(
        **user.dict(),
        hashed_password=user.password  # This should be hashed in a real app
    )
    
    users_db[user.username] = db_user
    return db_user

@router.get("/me", response_model=schemas.User)
async def read_current_user(
    current_user: str = Depends(require_authentication)
):
    """Get current user."""
    if current_user not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return users_db[current_user]

@router.get("/", response_model=List[schemas.User])
async def read_users(
    skip: int = 0, 
    limit: int = 100,
    current_user: str = Depends(require_authentication)
):
    """Get all users."""
    return list(users_db.values())[skip:skip + limit]
