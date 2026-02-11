from contextlib import asynccontextmanager
import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import redis

from routes.meetings import router as meetings_router
from routes.system import router as system_router


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


async def redis_event_listener() -> None:
  client = redis.Redis(host="redis", port=6379, decode_responses=True)
  pubsub = client.pubsub()
  pubsub.subscribe("events", "audio_segments")
  print("[WebSocket] Redis event listener started")

  loop = asyncio.get_running_loop()

  for message in pubsub.listen():
    if message["type"] != "message":
      continue
    try:
      event = json.loads(message["data"])
    except json.JSONDecodeError:
      continue
    await manager.broadcast(event)
    await asyncio.sleep(0)  # yield control


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[override]
  task = asyncio.create_task(redis_event_listener())
  yield
  task.cancel()


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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
  await manager.connect(websocket)
  try:
    while True:
      # keep connection alive, echo pings if needed
      msg = await websocket.receive_text()
      await websocket.send_text(f"ack:{msg}")
  except WebSocketDisconnect:
    manager.disconnect(websocket)


app.mount("/static", StaticFiles(directory="static", html=True), name="static")


@app.get("/")
async def serve_frontend() -> FileResponse:
  return FileResponse("static/index.html")


@app.get("/health")
async def health() -> dict:
  return {"status": "healthy", "service": "meetingbox-web"}


if __name__ == "__main__":
  import uvicorn

  uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

