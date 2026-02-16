import time

from fastapi import APIRouter
import psutil  # type: ignore

from database import get_connection


router = APIRouter()


@router.get("/status")
async def system_status() -> dict:
  cpu = psutil.cpu_percent(interval=0.5)
  mem = psutil.virtual_memory()
  disk = psutil.disk_usage("/")

  return {
    "system": {
      "cpu_percent": cpu,
      "memory_percent": mem.percent,
      "memory_used_gb": mem.used / (1024**3),
      "memory_total_gb": mem.total / (1024**3),
      "disk_percent": disk.percent,
      "disk_used_gb": disk.used / (1024**3),
      "disk_total_gb": disk.total / (1024**3),
    }
  }


@router.get("/device-info")
async def device_info() -> dict:
  """Extended device info consumed by the OLED touch-screen UI."""
  from routes.device import _load_settings, _get_wifi_info, _get_ip_address, _get_serial, FIRMWARE_VERSION

  settings = _load_settings()
  wifi = _get_wifi_info()
  disk = psutil.disk_usage("/")

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

