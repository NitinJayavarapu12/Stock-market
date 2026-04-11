from fastapi import Depends, HTTPException, Header
from typing import Optional


def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    """Verify Supabase JWT using the Supabase client (no JWT secret needed)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[7:]
    try:
        from backend.supabase_client import get_supabase
        sb = get_supabase()
        response = sb.auth.get_user(token)
        user = response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"sub": user.id, "email": user.email}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_user_id(user: dict = Depends(get_current_user)) -> str:
    return user["sub"]


def get_user_email(user: dict = Depends(get_current_user)) -> str:
    return user.get("email", "")
