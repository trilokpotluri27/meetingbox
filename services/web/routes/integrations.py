"""
Google Integrations Routes -- Device Authorization flow for Gmail and Calendar.

Uses the Google Device Code flow (RFC 8628) which is ideal for LAN appliances
since it doesn't require a public redirect URI. The user authorizes by visiting
google.com/device and entering a short code shown on screen.

Env vars required:
  GOOGLE_CLIENT_ID      -- from Google Cloud Console (Desktop or TVs & Limited Input type)
  GOOGLE_CLIENT_SECRET  -- from Google Cloud Console
"""

import logging
import os
import uuid
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from database import get_connection

logger = logging.getLogger(__name__)

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"

SCOPES_BY_PROVIDER = {
    "gmail": " ".join([
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
    ]),
    "calendar": " ".join([
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/userinfo.email",
    ]),
}

# Active device-code sessions: session_id -> {user_id, provider, device_code, interval, expires_at}
_pending_sessions: dict[str, dict] = {}


def _cleanup_expired_sessions():
    """Remove sessions whose device codes have expired."""
    now = datetime.utcnow().timestamp()
    expired = [sid for sid, s in _pending_sessions.items() if now > s["expires_at"]]
    for sid in expired:
        _pending_sessions.pop(sid, None)
    if expired:
        logger.debug("Cleaned up %d expired device-code sessions", len(expired))


def _check_google_configured():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars.",
        )


def _get_integration(user_id: str, provider: str) -> dict | None:
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM integrations WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        )
        return cur.fetchone()
    finally:
        conn.close()


def _build_credentials(integration: dict):
    """Build a google.oauth2.credentials.Credentials object from stored tokens."""
    from google.oauth2.credentials import Credentials

    expiry = None
    if integration.get("token_expiry"):
        try:
            expiry = datetime.fromisoformat(integration["token_expiry"])
        except (ValueError, TypeError):
            pass

    return Credentials(
        token=integration["access_token"],
        refresh_token=integration["refresh_token"],
        token_uri=TOKEN_URL,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        expiry=expiry,
        scopes=integration.get("scopes", "").split(" ") if integration.get("scopes") else [],
    )


def get_credentials_for_provider(user_id: str, provider: str):
    """Public helper used by the actions system. Returns refreshed Credentials or None."""
    integration = _get_integration(user_id, provider)
    if not integration:
        return None

    creds = _build_credentials(integration)

    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request as GoogleRequest
        try:
            creds.refresh(GoogleRequest())
            conn = get_connection()
            try:
                conn.execute(
                    "UPDATE integrations SET access_token = ?, token_expiry = ? WHERE id = ?",
                    (creds.token, creds.expiry.isoformat() if creds.expiry else None, integration["id"]),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.error("Token refresh failed for %s/%s: %s", user_id, provider, e)
            return None

    return creds


def _save_tokens(user_id: str, provider: str, token_data: dict, scopes: str):
    """Persist OAuth tokens and fetch the Google user email."""
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in")

    expiry = None
    if expires_in:
        from datetime import timedelta
        expiry = (datetime.utcnow() + timedelta(seconds=int(expires_in))).isoformat()

    email = ""
    try:
        from google.oauth2.credentials import Credentials
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=TOKEN_URL,
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
        )
        from googleapiclient.discovery import build
        service = build("oauth2", "v2", credentials=creds, cache_discovery=False)
        user_info = service.userinfo().get().execute()
        email = user_info.get("email", "")
    except Exception as e:
        logger.warning("Could not fetch Google user email: %s", e)

    integration_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM integrations WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        )
        conn.execute(
            """INSERT INTO integrations
               (id, user_id, provider, scopes, access_token, refresh_token, token_expiry, email, connected_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (integration_id, user_id, provider, scopes, access_token, refresh_token, expiry, email, now),
        )
        conn.commit()
    finally:
        conn.close()

    logger.info("Connected %s for user %s (email: %s)", provider, user_id, email)
    return {"email": email}


# ======================================================================
# LIST INTEGRATIONS
# ======================================================================

@router.get("/integrations")
async def list_integrations(current_user: dict = Depends(get_current_user)):
    """Return connection status for all supported integrations."""
    user_id = current_user["id"]
    results = []

    for provider_id, meta in [
        ("gmail", {"name": "Gmail", "icon": "mail", "description": "Send AI-drafted emails from meeting action items"}),
        ("calendar", {"name": "Google Calendar", "icon": "calendar", "description": "Create calendar events from meeting action items"}),
    ]:
        integration = _get_integration(user_id, provider_id)
        results.append({
            "id": provider_id,
            "name": meta["name"],
            "icon": meta["icon"],
            "description": meta["description"],
            "connected": integration is not None,
            "email": integration["email"] if integration else None,
        })

    return results


# ======================================================================
# DEVICE CODE FLOW: STEP 1 -- Request a device code
# ======================================================================

@router.post("/integrations/{provider}/device-code")
async def request_device_code(provider: str, current_user: dict = Depends(get_current_user)):
    """
    Start the Google Device Authorization flow.

    Returns a user_code and verification_url for the user to visit on any device.
    Also returns a session_id to poll for completion.
    """
    _check_google_configured()
    _cleanup_expired_sessions()

    if provider not in SCOPES_BY_PROVIDER:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    scopes = SCOPES_BY_PROVIDER[provider]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            DEVICE_CODE_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "scope": scopes,
            },
        )

    if resp.status_code != 200:
        logger.error("Device code request failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=502, detail="Failed to get device code from Google.")

    data = resp.json()

    session_id = str(uuid.uuid4())
    _pending_sessions[session_id] = {
        "user_id": current_user["id"],
        "provider": provider,
        "device_code": data["device_code"],
        "interval": data.get("interval", 5),
        "expires_at": datetime.utcnow().timestamp() + data.get("expires_in", 1800),
        "scopes": scopes,
    }

    return {
        "session_id": session_id,
        "user_code": data["user_code"],
        "verification_url": data["verification_url"],
        "expires_in": data.get("expires_in", 1800),
        "interval": data.get("interval", 5),
    }


# ======================================================================
# DEVICE CODE FLOW: STEP 2 -- Poll for token
# ======================================================================

@router.post("/integrations/{provider}/poll")
async def poll_device_code(provider: str, session_id: str = "", current_user: dict = Depends(get_current_user)):
    """
    Poll Google to check if the user has authorized the device code.

    Returns:
      - status: "pending" (keep polling), "complete" (tokens saved), "expired", "error"
    """
    if session_id not in _pending_sessions:
        raise HTTPException(status_code=404, detail="Unknown or expired session")

    session = _pending_sessions[session_id]

    if session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Session does not belong to this user")

    if datetime.utcnow().timestamp() > session["expires_at"]:
        _pending_sessions.pop(session_id, None)
        return {"status": "expired", "message": "Device code has expired. Please start again."}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "device_code": session["device_code"],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )

    token_data = resp.json()

    if resp.status_code == 200 and "access_token" in token_data:
        # Authorization complete
        _pending_sessions.pop(session_id, None)
        result = _save_tokens(
            user_id=session["user_id"],
            provider=session["provider"],
            token_data=token_data,
            scopes=session["scopes"],
        )
        return {
            "status": "complete",
            "provider": provider,
            "email": result.get("email", ""),
        }

    error = token_data.get("error", "")

    if error == "authorization_pending":
        return {"status": "pending", "message": "Waiting for user authorization..."}

    if error == "slow_down":
        return {"status": "pending", "message": "Polling too fast, slowing down...", "interval": session["interval"] + 2}

    if error == "expired_token":
        _pending_sessions.pop(session_id, None)
        return {"status": "expired", "message": "Device code has expired. Please start again."}

    if error == "access_denied":
        _pending_sessions.pop(session_id, None)
        return {"status": "denied", "message": "Authorization was denied by the user."}

    logger.error("Unexpected token poll response: %s", token_data)
    _pending_sessions.pop(session_id, None)
    return {"status": "error", "message": token_data.get("error_description", "Unknown error")}


# ======================================================================
# DISCONNECT
# ======================================================================

@router.post("/integrations/{provider}/disconnect")
async def disconnect_integration(provider: str, current_user: dict = Depends(get_current_user)):
    """Remove stored OAuth tokens for an integration."""
    user_id = current_user["id"]
    integration = _get_integration(user_id, provider)
    if not integration:
        raise HTTPException(status_code=404, detail=f"{provider} is not connected")

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                REVOKE_URL,
                params={"token": integration["access_token"]},
                timeout=10,
            )
    except Exception:
        pass

    conn = get_connection()
    try:
        conn.execute("DELETE FROM integrations WHERE user_id = ? AND provider = ?", (user_id, provider))
        conn.commit()
    finally:
        conn.close()

    logger.info("Disconnected %s for user %s", provider, user_id)
    return {"status": "disconnected", "provider": provider}
