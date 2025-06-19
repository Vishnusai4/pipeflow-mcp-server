"""
Token related schemas.
"""
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str | None = None

class TokenPayload(BaseModel):
    sub: str | None = None
