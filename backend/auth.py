import os
import jwt
from fastapi import Depends, HTTPException, Header
from typing import Optional


def _get_secret() -> str:
    secret = os.getenv("SUPABASE_JWT_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="Auth not configured")
    return secret


def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    """Verify Supabase JWT and return the payload (includes 'sub' = user_id)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[7:]
    try:
        payload = jwt.decode(
            token,
            _get_secret(),
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired — please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_user_id(user: dict = Depends(get_current_user)) -> str:
    return user["sub"]


def get_user_email(user: dict = Depends(get_current_user)) -> str:
    return user.get("email", "")
