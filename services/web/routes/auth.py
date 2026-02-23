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
        if not v.isalnum() and "_" not in v:
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
            "INSERT INTO users (id, username, password_hash, display_name, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, body.username, hashed, body.display_name or body.username, "admin", now),
        )
        conn.commit()
    finally:
        conn.close()

    token = create_access_token({"sub": user_id, "role": "admin"})
    logger.info("First admin user created: %s", body.username)
    return {
        "token": token,
        "user": {
            "id": user_id,
            "username": body.username,
            "display_name": body.display_name or body.username,
            "role": "admin",
        },
    }


@router.post("/register")
async def register(body: RegisterRequest, current_user: dict = Depends(get_current_user)):
    """Register a new user (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create users")

    if get_user_by_username(body.username):
        raise HTTPException(status_code=409, detail="Username already taken")

    user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    hashed = hash_password(body.password)

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (id, username, password_hash, display_name, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, body.username, hashed, body.display_name or body.username, "user", now),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "user": {
            "id": user_id,
            "username": body.username,
            "display_name": body.display_name or body.username,
            "role": "user",
        }
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
        "user": {
            "id": user["id"],
            "username": user["username"],
            "display_name": user["display_name"],
            "role": user["role"],
        },
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "display_name": current_user["display_name"],
        "role": current_user["role"],
    }
