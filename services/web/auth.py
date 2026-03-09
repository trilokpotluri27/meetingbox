"""
Authentication utilities -- JWT tokens and password hashing.
"""

import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from database import get_connection

logger = logging.getLogger(__name__)
_WEAK_DEFAULT_SECRET = "meetingbox-dev-secret-change-in-production"


def _load_secret_key() -> str:
    configured = os.getenv("JWT_SECRET_KEY", "").strip()
    if configured and configured != _WEAK_DEFAULT_SECRET:
        return configured

    # Never use a known static secret. Fall back to an ephemeral secret so
    # deployments without JWT_SECRET_KEY fail safe instead of being forgeable.
    ephemeral = secrets.token_urlsafe(48)
    if configured == _WEAK_DEFAULT_SECRET:
        logger.warning(
            "Weak JWT_SECRET_KEY value detected and ignored. "
            "Set a strong JWT_SECRET_KEY in the environment."
        )
    else:
        logger.warning(
            "JWT_SECRET_KEY is not set. Using an ephemeral in-memory key; "
            "existing tokens will be invalid after restart."
        )
    return ephemeral


SECRET_KEY = _load_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "720"))  # 30 days default

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_user_by_username(username: str) -> Optional[dict]:
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        return cur.fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id: str) -> Optional[dict]:
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return cur.fetchone()
    finally:
        conn.close()


def count_users() -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        return cur.fetchone()[0]
    finally:
        conn.close()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """FastAPI dependency -- extracts and validates JWT, returns user dict."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """Like get_current_user but returns None instead of raising."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
