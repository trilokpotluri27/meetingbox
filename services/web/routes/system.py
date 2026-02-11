from fastapi import APIRouter
import psutil  # type: ignore


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

