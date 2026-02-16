from contextlib import asynccontextmanager
import asyncio
import json
import threading

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import redis

from database import init_database
from routes.meetings import router as meetings_router
from routes.system import router as system_router
from routes.device import router as device_router

# Ensure all DB tables exist (including local_summaries) on startup
init_database()


class ConnectionManager:
  def __init__(self) -> None:
    self.active_connections: list[WebSocket] = []

  async def connect(self, websocket: WebSocket) -> None:
    await websocket.accept()
    self.active_connections.append(websocket)
    print(f"[WebSocket] Client connected ({len(self.active_connections)} total)")

  def disconnect(self, websocket: WebSocket) -> None:
    if websocket in self.active_connections:
      self.active_connections.remove(websocket)
      print(f"[WebSocket] Client disconnected ({len(self.active_connections)} total)")

  async def broadcast(self, message: dict) -> None:
    dead: list[WebSocket] = []
    for ws in self.active_connections:
      try:
        await ws.send_json(message)
      except Exception as exc:
        print(f"[WebSocket] Error sending to client: {exc}")
        dead.append(ws)
    for ws in dead:
      self.disconnect(ws)


manager = ConnectionManager()

def _redis_listener_thread(queue: asyncio.Queue, loop: asyncio.AbstractEventLoop) -> None:
  """Blocking Redis pubsub loop - runs in a separate thread so it doesn't block the event loop."""
  client = redis.Redis(host="redis", port=6379, decode_responses=True)
  pubsub = client.pubsub()
  pubsub.subscribe("events", "audio_segments")
  print("[WebSocket] Redis event listener started")
  for message in pubsub.listen():
    if message.get("type") != "message":
      continue
    try:
      event = json.loads(message["data"])
      loop.call_soon_threadsafe(queue.put_nowait, event)
    except json.JSONDecodeError:
      continue


async def _redis_event_relay(queue: asyncio.Queue) -> None:
  """Async task: read from queue and broadcast to WebSocket clients."""
  while True:
    try:
      event = await asyncio.wait_for(queue.get(), timeout=1.0)
      await manager.broadcast(event)
    except asyncio.TimeoutError:
      continue


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[override]
  loop = asyncio.get_running_loop()
  queue: asyncio.Queue = asyncio.Queue()
  thread = threading.Thread(target=_redis_listener_thread, args=(queue, loop), daemon=True)
  thread.start()
  relay = asyncio.create_task(_redis_event_relay(queue))
  yield
  relay.cancel()


app = FastAPI(title="MeetingBox API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(meetings_router, prefix="/api/meetings", tags=["meetings"])
app.include_router(system_router, prefix="/api/system", tags=["system"])
app.include_router(device_router, prefix="/api/device", tags=["device"])


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
  await manager.connect(websocket)
  try:
    while True:
      msg = await websocket.receive_text()
      await websocket.send_text(f"ack:{msg}")
  except WebSocketDisconnect:
    manager.disconnect(websocket)


# Serve SPA: / and /assets/* from static (frontend/dist). Must be last so /api and /ws take precedence.
app.mount("/", StaticFiles(directory="static", html=True), name="static")


@app.get("/health")
async def health() -> dict:
  return {"status": "healthy", "service": "meetingbox-web"}


if __name__ == "__main__":
  import uvicorn

  uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

