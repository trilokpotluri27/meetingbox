"""
Authentication Routes -- register, login, user management.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_user_by_username,
    count_users,
    get_current_user,
)
from database import get_connection

logger = logging.getLogger(__name__)

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not all(c.isalnum() or c == '_' for c in v):
            raise ValueError("Username must be alphanumeric (underscores allowed)")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


@router.get("/has-users")
async def has_users():
    """Check whether any users exist (used by onboarding)."""
    return {"has_users": count_users() > 0}


def _user_response(user_id: str, username: str, display_name: str, role: str, onboarding_complete: int) -> dict:
    """Build a consistent user dict for auth responses."""
    return {
        "id": user_id,
        "username": username,
        "display_name": display_name,
        "role": role,
        "onboarding_complete": bool(onboarding_complete),
    }


@router.post("/setup")
async def setup_first_user(body: RegisterRequest):
    """Create the first admin user. Only works when no users exist."""
    if count_users() > 0:
        raise HTTPException(status_code=400, detail="Setup already completed. Use /login.")

    user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    hashed = hash_password(body.password)

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (id, username, password_hash, display_name, role, onboarding_complete, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, body.username, hashed, body.display_name or body.username, "admin", 0, now),
        )
        conn.commit()
    finally:
        conn.close()

    token = create_access_token({"sub": user_id, "role": "admin"})
    logger.info("First admin user created: %s", body.username)
    return {
        "token": token,
        "user": _user_response(user_id, body.username, body.display_name or body.username, "admin", 0),
    }


@router.post("/register")
async def register(body: RegisterRequest):
    """Self-register a new user. Open to anyone on the network."""
    if get_user_by_username(body.username):
        raise HTTPException(status_code=409, detail="Username already taken")

    user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    hashed = hash_password(body.password)

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (id, username, password_hash, display_name, role, onboarding_complete, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, body.username, hashed, body.display_name or body.username, "user", 0, now),
        )
        conn.commit()
    finally:
        conn.close()

    token = create_access_token({"sub": user_id, "role": "user"})
    logger.info("New user registered: %s", body.username)
    return {
        "token": token,
        "user": _user_response(user_id, body.username, body.display_name or body.username, "user", 0),
    }


@router.post("/login")
async def login(body: LoginRequest):
    """Authenticate and return a JWT token."""
    user = get_user_by_username(body.username.strip().lower())
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": user["id"], "role": user["role"]})
    return {
        "token": token,
        "user": _user_response(
            user["id"], user["username"], user["display_name"],
            user["role"], user.get("onboarding_complete", 0),
        ),
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return _user_response(
        current_user["id"], current_user["username"], current_user["display_name"],
        current_user["role"], current_user.get("onboarding_complete", 0),
    )


@router.post("/complete-onboarding")
async def complete_onboarding(current_user: dict = Depends(get_current_user)):
    """Mark the authenticated user's onboarding as complete."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET onboarding_complete = 1 WHERE id = ?",
            (current_user["id"],),
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "ok"}
