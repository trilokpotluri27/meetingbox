"""
Device Management Routes

Endpoints used by the OLED touchscreen device-ui.
Manages: settings, WiFi, updates, system device info.
"""

import json
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psutil

from database import get_connection

router = APIRouter()

# Persistent settings file on disk
SETTINGS_FILE = Path(os.getenv("DEVICE_SETTINGS_PATH", "/data/config/device_settings.json"))
SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

FIRMWARE_VERSION = os.getenv("FIRMWARE_VERSION", "1.0.0")
DEVICE_MODEL = "MeetingBox v1.0"

# Boot time for uptime calculation
_BOOT_TIME = time.time()


# ======================================================================
# HELPERS
# ======================================================================

def _load_settings() -> dict:
    """Load device settings from disk, with defaults."""
    defaults = {
        "device_name": "MeetingBox",
        "timezone": "UTC",
        "auto_delete_days": "never",
        "brightness": "high",
        "screen_timeout": "never",
        "privacy_mode": False,
    }
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE) as f:
                saved = json.load(f)
            defaults.update(saved)
        except Exception:
            pass
    return defaults


def _save_settings(settings: dict) -> None:
    """Persist settings to disk."""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


def _get_wifi_info() -> dict:
    """Get current WiFi SSID and signal on Linux."""
    ssid = ""
    signal = 0
    try:
        result = subprocess.run(
            ["iwgetid", "-r"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            ssid = result.stdout.strip()
        sig_result = subprocess.run(
            ["iwconfig"], capture_output=True, text=True, timeout=5)
        for line in sig_result.stdout.splitlines():
            if "Signal level" in line:
                # Parse "Signal level=-XX dBm"
                idx = line.index("Signal level=")
                val = line[idx + 13:].split()[0].replace("dBm", "")
                dbm = int(val)
                # Convert dBm to percentage (rough)
                signal = max(0, min(100, 2 * (dbm + 100)))
    except Exception:
        pass
    return {"ssid": ssid, "signal": signal}


def _get_ip_address() -> str:
    """Get primary IP address."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""


def _get_serial() -> str:
    """Read Raspberry Pi serial number."""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("Serial"):
                    return "MB-" + line.split(":")[1].strip()[-8:]
    except Exception:
        pass
    return "MB-00000000"


# ======================================================================
# SETTINGS
# ======================================================================

@router.get("/settings")
async def get_settings():
    """Return current device settings."""
    return _load_settings()


class SettingsUpdate(BaseModel):
    device_name: Optional[str] = None
    timezone: Optional[str] = None
    auto_delete_days: Optional[str] = None
    brightness: Optional[str] = None
    screen_timeout: Optional[str] = None
    privacy_mode: Optional[bool] = None
    action: Optional[str] = None  # restart / factory_reset


@router.patch("/settings")
async def update_settings(body: SettingsUpdate):
    """Update one or more device settings."""
    current = _load_settings()
    updates = body.dict(exclude_none=True)

    # Handle special actions
    action = updates.pop("action", None)
    if action == "restart":
        # Schedule restart in background
        try:
            subprocess.Popen(["sudo", "reboot"], close_fds=True)
        except Exception:
            pass
        return {"status": "restarting"}

    if action == "factory_reset":
        # Delete settings and setup marker, then reboot
        try:
            SETTINGS_FILE.unlink(missing_ok=True)
            # Remove setup marker from shared config volume
            for p in ["/data/config/.setup_complete",
                      "/opt/meetingbox/.setup_complete"]:
                Path(p).unlink(missing_ok=True)
            subprocess.Popen(["sudo", "reboot"], close_fds=True)
        except Exception:
            pass
        return {"status": "resetting"}

    current.update(updates)
    _save_settings(current)
    return current


# ======================================================================
# DEVICE INFO (extended system info for OLED UI)
# ======================================================================

@router.get("/device-info")
async def device_info():
    """
    Extended system info for the OLED display.
    Returns everything the device-ui HomeScreen footer + Settings need.
    """
    settings = _load_settings()
    wifi = _get_wifi_info()
    disk = psutil.disk_usage("/")

    # Count meetings
    meetings_count = 0
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM meetings")
        meetings_count = cur.fetchone()[0]
        conn.close()
    except Exception:
        pass

    uptime_seconds = int(time.time() - psutil.boot_time())

    return {
        "device_name": settings.get("device_name", "MeetingBox"),
        "serial_number": _get_serial(),
        "firmware_version": FIRMWARE_VERSION,
        "ip_address": _get_ip_address(),
        "wifi_ssid": wifi["ssid"],
        "wifi_signal": wifi["signal"],
        "storage_used": disk.used,
        "storage_total": disk.total,
        "uptime": uptime_seconds,
        "meetings_count": meetings_count,
    }


# ======================================================================
# WIFI
# ======================================================================

@router.get("/wifi/scan")
async def wifi_scan():
    """Scan for available WiFi networks."""
    networks = []
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,ACTIVE", "dev", "wifi", "list"],
            capture_output=True, text=True, timeout=15,
        )
        for line in result.stdout.strip().splitlines():
            parts = line.split(":")
            if len(parts) >= 4 and parts[0]:
                networks.append({
                    "ssid": parts[0],
                    "signal_strength": int(parts[1]) if parts[1].isdigit() else 0,
                    "security": parts[2] or "open",
                    "connected": parts[3] == "yes",
                })
    except Exception as e:
        # Fallback: return current connection only
        wifi = _get_wifi_info()
        if wifi["ssid"]:
            networks.append({
                "ssid": wifi["ssid"],
                "signal_strength": wifi["signal"],
                "security": "wpa2",
                "connected": True,
            })
    return networks


class WiFiConnect(BaseModel):
    ssid: str
    password: Optional[str] = None


@router.post("/wifi/connect")
async def wifi_connect(body: WiFiConnect):
    """Connect to a WiFi network using NetworkManager."""
    try:
        cmd = ["nmcli", "dev", "wifi", "connect", body.ssid]
        if body.password:
            cmd += ["password", body.password]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return {"status": "connected", "message": f"Connected to {body.ssid}"}
        else:
            return {"status": "failed", "message": result.stderr.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wifi/disconnect")
async def wifi_disconnect():
    """Disconnect from current WiFi."""
    try:
        subprocess.run(
            ["nmcli", "dev", "disconnect", "wlan0"],
            capture_output=True, text=True, timeout=10,
        )
        return {"status": "disconnected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ======================================================================
# UPDATES
# ======================================================================

@router.get("/check-updates")
async def check_updates():
    """Check for firmware updates (placeholder – real impl would check a server)."""
    return {
        "update_available": False,
        "current_version": FIRMWARE_VERSION,
        "latest_version": None,
        "release_notes": None,
    }


@router.post("/install-update")
async def install_update():
    """Install firmware update (placeholder)."""
    return {"status": "no_update_available"}


# ======================================================================
# INTEGRATIONS (placeholder)
# ======================================================================

@router.get("/integrations")
async def list_integrations():
    """List integration statuses."""
    return [
        {"id": "gmail", "name": "Gmail", "connected": False},
        {"id": "calendar", "name": "Google Calendar", "connected": False},
    ]
