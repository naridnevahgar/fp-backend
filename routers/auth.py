from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import create_jwt, get_current_user, verify_google_token
from db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    token: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    email: str
    name: str
    picture: str | None = None
    role: str


@router.post("/google", response_model=AuthResponse)
async def google_login(body: GoogleLoginRequest):
    """Verify Google ID token, create/fetch user, return JWT."""
    idinfo = verify_google_token(body.token)

    db = get_db()
    users = db["users"]

    user = users.find_one({"google_id": idinfo["sub"]})
    if not user:
        user = {
            "google_id": idinfo["sub"],
            "email": idinfo["email"],
            "name": idinfo.get("name", ""),
            "picture": idinfo.get("picture", ""),
            "role": "user",
            "created_at": datetime.now(timezone.utc),
        }
        users.insert_one(user)

    token = create_jwt(user)
    return AuthResponse(
        access_token=token,
        user={
            "email": user["email"],
            "name": user["name"],
            "picture": user.get("picture", ""),
            "role": user["role"],
        },
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """Return current authenticated user info."""
    return UserResponse(
        email=user["email"],
        name=user["name"],
        picture=user.get("picture"),
        role=user["role"],
    )
