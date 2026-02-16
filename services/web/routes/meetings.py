import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
import redis
import shutil
import httpx

from database import get_connection

# Lazy-loaded Anthropic client for on-demand summarization
_anthropic_client = None

def _get_anthropic_client():
  global _anthropic_client
  if _anthropic_client is None:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
      return None
    from anthropic import Anthropic
    _anthropic_client = Anthropic(api_key=api_key)
  return _anthropic_client

# Ollama configuration for local summarization
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "phi3:mini")

router = APIRouter()
REDIS = redis.Redis(host="redis", port=6379, decode_responses=True)
RECORDINGS_DIR = Path("/data/audio/recordings")
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

# Accepted upload extensions; non-WAV are converted with ffmpeg to 16kHz mono WAV
UPLOAD_AUDIO_EXTENSIONS = {".wav", ".webm", ".ogg", ".mp4", ".m4a"}


class MeetingResponse(BaseModel):
  id: str
  title: str
  start_time: str
  end_time: Optional[str]
  duration: Optional[int]
  status: str
  audio_path: Optional[str]
  created_at: str


class TranscriptSegment(BaseModel):
  segment_num: int
  start_time: float
  end_time: float
  text: str
  speaker_id: Optional[str] = None


class MeetingSummary(BaseModel):
  summary: str
  action_items: list[dict]
  decisions: list
  topics: list
  sentiment: str


class LocalSummary(BaseModel):
  summary: str
  action_items: list[dict]
  decisions: list
  topics: list
  sentiment: str
  model_name: str


def _normalize_summary_data(data: dict) -> dict:
  """Normalize LLM output so decisions/topics are always lists of strings.
  LLMs sometimes return decisions as objects like {"decision": "...", "responsible_party": null}
  instead of plain strings. This coerces everything to strings."""
  # Normalize decisions
  raw_decisions = data.get("decisions", [])
  decisions = []
  for d in raw_decisions:
    if isinstance(d, str):
      decisions.append(d)
    elif isinstance(d, dict):
      # Extract the text from common LLM object shapes
      decisions.append(d.get("decision") or d.get("text") or d.get("description") or str(d))
    else:
      decisions.append(str(d))
  data["decisions"] = decisions

  # Normalize topics
  raw_topics = data.get("topics", [])
  topics = []
  for t in raw_topics:
    if isinstance(t, str):
      topics.append(t)
    elif isinstance(t, dict):
      topics.append(t.get("topic") or t.get("name") or t.get("text") or str(t))
    else:
      topics.append(str(t))
  data["topics"] = topics

  # Normalize action_items (ensure they're dicts)
  raw_actions = data.get("action_items", [])
  actions = []
  for a in raw_actions:
    if isinstance(a, dict):
      actions.append(a)
    elif isinstance(a, str):
      actions.append({"task": a, "assignee": None, "due_date": None})
    else:
      actions.append({"task": str(a), "assignee": None, "due_date": None})
  data["action_items"] = actions

  # Ensure sentiment is a string
  sentiment = data.get("sentiment", "")
  if not isinstance(sentiment, str):
    data["sentiment"] = str(sentiment)

  return data


class MeetingDetail(BaseModel):
  meeting: MeetingResponse
  segments: List[TranscriptSegment]
  summary: Optional[MeetingSummary]
  local_summary: Optional[LocalSummary]


# --- Start / Stop meeting (wire to Redis for audio service) ---

@router.post("/start")
async def start_meeting():
  """Start a new recording. Sends command to audio service via Redis."""
  session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
  REDIS.publish("commands", json.dumps({"action": "start_recording", "session_id": session_id}))
  REDIS.set("current_meeting_id", session_id)
  REDIS.set("recording_state", "recording")
  return {"session_id": session_id, "status": "recording_started"}


@router.post("/stop")
async def stop_meeting():
  """Stop the current recording. Sends command to audio service via Redis."""
  session_id = REDIS.get("current_meeting_id")
  REDIS.publish(
    "commands",
    json.dumps({"action": "stop_recording", "session_id": session_id}),
  )
  REDIS.set("recording_state", "processing")
  if session_id:
    REDIS.delete("current_meeting_id")
  return {"session_id": session_id, "status": "recording_stopped"}


@router.get("/recording-status")
async def recording_status():
  """Current recording state for the dashboard."""
  state = REDIS.get("recording_state") or "idle"
  current_id = REDIS.get("current_meeting_id")
  return {"state": state, "session_id": current_id}


@router.post("/reset-recording-state")
async def reset_recording_state():
  """Clear recording state so the dashboard shows Start/Record buttons again (e.g. if stuck on Processing)."""
  REDIS.set("recording_state", "idle")
  REDIS.delete("current_meeting_id")
  return {"status": "idle"}


# --- Test WAV ingest (bypass mic: feed a WAV file into transcription → AI pipeline) ---

@router.post("/test/ingest-wav")
async def ingest_test_wav(file: UploadFile = File(...)):
  """
  Upload a WAV file to run through the full pipeline (transcription → summary).
  Use this to test without a microphone. Session ID is derived from filename or timestamp.
  """
  if not file.filename or not file.filename.lower().endswith(".wav"):
    raise HTTPException(status_code=400, detail="Upload must be a .wav file")
  session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
  dest = RECORDINGS_DIR / f"{session_id}.wav"
  try:
    with dest.open("wb") as f:
      shutil.copyfileobj(file.file, f)
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

  # Emit the same event the audio service would: transcription service will pick it up
  REDIS.publish(
    "events",
    json.dumps({
      "type": "recording_stopped",
      "session_id": session_id,
      "path": str(dest),
      "timestamp": datetime.now().isoformat(),
    }),
  )
  return {"session_id": session_id, "path": str(dest), "status": "ingested"}


def _ensure_16k_mono_wav(source: Path, dest: Path) -> None:
  """Convert source audio to 16kHz mono WAV at dest using ffmpeg."""
  subprocess.run(
    [
      "ffmpeg",
      "-y",
      "-i",
      str(source),
      "-acodec",
      "pcm_s16le",
      "-ar",
      "16000",
      "-ac",
      "1",
      str(dest),
    ],
    check=True,
    capture_output=True,
    timeout=300,
  )


@router.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
  """
  Upload audio from your computer (e.g. browser recording). Accepts WAV, WebM, OGG, MP4.
  Converts to 16kHz mono WAV and runs the same pipeline (transcription → summary).
  Use this to record with your PC mic: record in the browser, then upload.
  """
  fn = (file.filename or "").lower()
  ext = Path(fn).suffix or ".webm"
  if ext not in UPLOAD_AUDIO_EXTENSIONS:
    # Browser may send blob without extension; treat as webm
    ext = ".webm"
  session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
  dest_wav = RECORDINGS_DIR / f"{session_id}.wav"

  with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
    tmp_path = Path(tmp.name)
  try:
    content = await file.read()
    tmp_path.write_bytes(content)
    _ensure_16k_mono_wav(tmp_path, dest_wav)
  except subprocess.CalledProcessError as e:
    raise HTTPException(
      status_code=400,
      detail=f"Audio conversion failed (unsupported format?): {e.stderr.decode() if e.stderr else str(e)}",
    )
  finally:
    tmp_path.unlink(missing_ok=True)

  REDIS.set("recording_state", "processing")
  REDIS.set("current_meeting_id", session_id)
  REDIS.publish(
    "events",
    json.dumps({
      "type": "recording_stopped",
      "session_id": session_id,
      "path": str(dest_wav),
      "timestamp": datetime.now().isoformat(),
    }),
  )
  return {"session_id": session_id, "path": str(dest_wav), "status": "ingested"}


@router.get("/", response_model=List[MeetingResponse])
async def list_meetings(limit: int = 50, offset: int = 0, status: Optional[str] = None):
  conn = get_connection()
  conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}  # type: ignore
  cur = conn.cursor()

  query = "SELECT * FROM meetings"
  params: list[object] = []
  if status:
    query += " WHERE status = ?"
    params.append(status)
  query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
  params.extend([limit, offset])

  cur.execute(query, params)
  rows = cur.fetchall()
  conn.close()

  return rows


@router.post("/{meeting_id}/summarize")
async def summarize_meeting(meeting_id: str):
  """Generate an AI summary for a transcribed meeting using Claude."""
  client = _get_anthropic_client()
  if not client:
    raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY is not configured on the server.")

  conn = get_connection()
  conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
  cur = conn.cursor()

  # Check meeting exists
  cur.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
  meeting = cur.fetchone()
  if not meeting:
    conn.close()
    raise HTTPException(status_code=404, detail="Meeting not found")

  # Check if summary already exists
  cur.execute("SELECT * FROM summaries WHERE meeting_id = ?", (meeting_id,))
  existing = cur.fetchone()
  if existing:
    conn.close()
    result = _normalize_summary_data({
      "summary": existing["summary"],
      "action_items": json.loads(existing["action_items"] or "[]"),
      "decisions": json.loads(existing["decisions"] or "[]"),
      "topics": json.loads(existing["topics"] or "[]"),
      "sentiment": existing["sentiment"],
    })
    result["status"] = "already_exists"
    return result

  # Fetch transcript segments
  cur.execute(
    "SELECT segment_num, start_time, text FROM segments WHERE meeting_id = ? ORDER BY segment_num",
    (meeting_id,),
  )
  rows = cur.fetchall()
  conn.close()

  if not rows:
    raise HTTPException(status_code=400, detail="No transcript segments found for this meeting.")

  # Build transcript text
  parts = []
  for r in rows:
    mins = int((r["start_time"] or 0) // 60)
    secs = int((r["start_time"] or 0) % 60)
    parts.append(f"[{mins:02d}:{secs:02d}] Segment {r['segment_num']}: {r['text']}")
  transcript = "\n\n".join(parts)

  prompt = (
    "You are analyzing a meeting transcript. Please provide:\n\n"
    "1. Summary (2-3 sentences)\n"
    "2. Key discussion points (3-5 bullets)\n"
    "3. Decisions made\n"
    "4. Action items with assignees if available\n"
    "5. 3-5 topic hashtags\n"
    "6. Overall sentiment (single word or short phrase)\n\n"
    "Return **only** valid JSON in this shape:\n"
    '{\n'
    '  "summary": "...",\n'
    '  "discussion_points": ["...", "..."],\n'
    '  "decisions": ["...", "..."],\n'
    '  "action_items": [{"task": "...", "assignee": "...", "due_date": "..."}],\n'
    '  "topics": ["#topic1", "#topic2"],\n'
    '  "sentiment": "Productive"\n'
    "}\n\n"
    f"Transcript:\n\n{transcript}"
  )

  model = os.getenv("AI_MODEL", "claude-sonnet-4-20250514")
  max_tokens = int(os.getenv("AI_MAX_TOKENS", "2000"))

  try:
    resp = client.messages.create(
      model=model,
      max_tokens=max_tokens,
      messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text
  except Exception as exc:
    raise HTTPException(status_code=500, detail=f"Claude API error: {exc}")

  # Parse JSON from response
  if "```json" in text:
    start = text.find("```json") + len("```json")
    end = text.find("```", start)
    json_str = text[start:end].strip()
  else:
    json_str = text.strip()

  try:
    data = json.loads(json_str)
  except json.JSONDecodeError:
    raise HTTPException(status_code=500, detail="Failed to parse JSON from Claude response.")

  # Normalize LLM output (decisions/topics may be objects instead of strings)
  data = _normalize_summary_data(data)

  # Save to DB
  conn = get_connection()
  cur = conn.cursor()
  cur.execute(
    """
    INSERT OR REPLACE INTO summaries
      (meeting_id, summary, action_items, decisions, topics, sentiment, generated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    (
      meeting_id,
      data.get("summary", ""),
      json.dumps(data.get("action_items", [])),
      json.dumps(data.get("decisions", [])),
      json.dumps(data.get("topics", [])),
      data.get("sentiment", ""),
      datetime.now().isoformat(),
    ),
  )
  cur.execute("UPDATE meetings SET status = 'completed', end_time = ? WHERE id = ?", (datetime.now().isoformat(), meeting_id))
  conn.commit()
  conn.close()

  return {
    "status": "generated",
    "summary": data.get("summary", ""),
    "action_items": data.get("action_items", []),
    "decisions": data.get("decisions", []),
    "topics": data.get("topics", []),
    "sentiment": data.get("sentiment", ""),
  }


@router.post("/{meeting_id}/summarize-local")
async def summarize_meeting_local(meeting_id: str):
  """Generate a summary using the local Ollama LLM (no API key needed)."""
  conn = get_connection()
  conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
  cur = conn.cursor()

  # Check meeting exists
  cur.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
  meeting = cur.fetchone()
  if not meeting:
    conn.close()
    raise HTTPException(status_code=404, detail="Meeting not found")

  # Check if local summary already exists
  cur.execute("SELECT * FROM local_summaries WHERE meeting_id = ?", (meeting_id,))
  existing = cur.fetchone()
  if existing:
    conn.close()
    result = _normalize_summary_data({
      "summary": existing["summary"],
      "action_items": json.loads(existing["action_items"] or "[]"),
      "decisions": json.loads(existing["decisions"] or "[]"),
      "topics": json.loads(existing["topics"] or "[]"),
      "sentiment": existing["sentiment"],
    })
    result["status"] = "already_exists"
    result["model_name"] = existing.get("model_name", LOCAL_LLM_MODEL)
    return result

  # Fetch transcript segments
  cur.execute(
    "SELECT segment_num, start_time, text FROM segments WHERE meeting_id = ? ORDER BY segment_num",
    (meeting_id,),
  )
  rows = cur.fetchall()
  conn.close()

  if not rows:
    raise HTTPException(status_code=400, detail="No transcript segments found for this meeting.")

  # Build transcript text
  parts = []
  for r in rows:
    mins = int((r["start_time"] or 0) // 60)
    secs = int((r["start_time"] or 0) % 60)
    parts.append(f"[{mins:02d}:{secs:02d}] Segment {r['segment_num']}: {r['text']}")
  transcript = "\n\n".join(parts)

  prompt = (
    "You are analyzing a meeting transcript. Please provide:\n\n"
    "1. Summary (2-3 sentences)\n"
    "2. Key discussion points (3-5 bullets)\n"
    "3. Decisions made\n"
    "4. Action items with assignees if available\n"
    "5. 3-5 topic hashtags\n"
    "6. Overall sentiment (single word or short phrase)\n\n"
    "Return **only** valid JSON with no additional text, in this exact shape:\n"
    '{\n'
    '  "summary": "...",\n'
    '  "discussion_points": ["...", "..."],\n'
    '  "decisions": ["...", "..."],\n'
    '  "action_items": [{"task": "...", "assignee": "...", "due_date": "..."}],\n'
    '  "topics": ["#topic1", "#topic2"],\n'
    '  "sentiment": "Productive"\n'
    "}\n\n"
    f"Transcript:\n\n{transcript}"
  )

  # Call Ollama API
  try:
    # First, check if Ollama is reachable and model is available
    resp = httpx.post(
      f"{OLLAMA_HOST}/api/generate",
      json={
        "model": LOCAL_LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
          "temperature": 0.3,
          "num_predict": 2000,
        },
      },
      timeout=300.0,  # Local inference can take a while
    )
    resp.raise_for_status()
    result = resp.json()
    text = result.get("response", "")
  except httpx.ConnectError:
    raise HTTPException(
      status_code=503,
      detail=(
        f"Cannot connect to Ollama at {OLLAMA_HOST}. "
        "Make sure the ollama container is running: docker compose ps"
      ),
    )
  except httpx.HTTPStatusError as exc:
    error_body = exc.response.text
    if "not found" in error_body.lower():
      raise HTTPException(
        status_code=503,
        detail=(
          f"Model '{LOCAL_LLM_MODEL}' not found in Ollama. "
          f"Pull it first: docker compose exec ollama ollama pull {LOCAL_LLM_MODEL}"
        ),
      )
    raise HTTPException(status_code=500, detail=f"Ollama error: {error_body}")
  except Exception as exc:
    raise HTTPException(status_code=500, detail=f"Local LLM error: {exc}")

  # Parse JSON from response
  if "```json" in text:
    start = text.find("```json") + len("```json")
    end = text.find("```", start)
    json_str = text[start:end].strip()
  elif "```" in text:
    start = text.find("```") + len("```")
    end = text.find("```", start)
    json_str = text[start:end].strip()
  else:
    # Try to find JSON object in the response
    json_start = text.find("{")
    json_end = text.rfind("}") + 1
    if json_start >= 0 and json_end > json_start:
      json_str = text[json_start:json_end].strip()
    else:
      json_str = text.strip()

  try:
    data = json.loads(json_str)
  except json.JSONDecodeError:
    raise HTTPException(
      status_code=500,
      detail=f"Failed to parse JSON from local LLM response. Raw output: {text[:500]}",
    )

  # Normalize LLM output (decisions/topics may be objects instead of strings)
  data = _normalize_summary_data(data)

  # Save to local_summaries table
  conn = get_connection()
  cur = conn.cursor()
  cur.execute(
    """
    INSERT OR REPLACE INTO local_summaries
      (meeting_id, summary, action_items, decisions, topics, sentiment, model_name, generated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
      meeting_id,
      data.get("summary", ""),
      json.dumps(data.get("action_items", [])),
      json.dumps(data.get("decisions", [])),
      json.dumps(data.get("topics", [])),
      data.get("sentiment", ""),
      LOCAL_LLM_MODEL,
      datetime.now().isoformat(),
    ),
  )
  conn.commit()
  conn.close()

  return {
    "status": "generated",
    "summary": data.get("summary", ""),
    "action_items": data.get("action_items", []),
    "decisions": data.get("decisions", []),
    "topics": data.get("topics", []),
    "sentiment": data.get("sentiment", ""),
    "model_name": LOCAL_LLM_MODEL,
  }


@router.get("/{meeting_id}", response_model=MeetingDetail)
async def get_meeting(meeting_id: str):
  conn = get_connection()
  conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}  # type: ignore
  cur = conn.cursor()

  cur.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
  meeting = cur.fetchone()
  if not meeting:
    conn.close()
    raise HTTPException(status_code=404, detail="Meeting not found")

  cur.execute(
    """
    SELECT segment_num, start_time, end_time, text, speaker_id
    FROM segments
    WHERE meeting_id = ?
    ORDER BY segment_num
    """,
    (meeting_id,),
  )
  segments_rows = cur.fetchall()

  cur.execute("SELECT * FROM summaries WHERE meeting_id = ?", (meeting_id,))
  summary_row = cur.fetchone()

  cur.execute("SELECT * FROM local_summaries WHERE meeting_id = ?", (meeting_id,))
  local_summary_row = cur.fetchone()
  conn.close()

  segments = [
    {
      "segment_num": r["segment_num"],
      "start_time": r["start_time"],
      "end_time": r["end_time"],
      "text": r["text"],
      "speaker_id": r.get("speaker_id"),
    }
    for r in segments_rows
  ]

  summary = None
  if summary_row:
    summary = _normalize_summary_data({
      "summary": summary_row["summary"],
      "action_items": json.loads(summary_row["action_items"] or "[]"),
      "decisions": json.loads(summary_row["decisions"] or "[]"),
      "topics": json.loads(summary_row["topics"] or "[]"),
      "sentiment": summary_row["sentiment"],
    })

  local_summary = None
  if local_summary_row:
    local_summary = _normalize_summary_data({
      "summary": local_summary_row["summary"],
      "action_items": json.loads(local_summary_row["action_items"] or "[]"),
      "decisions": json.loads(local_summary_row["decisions"] or "[]"),
      "topics": json.loads(local_summary_row["topics"] or "[]"),
      "sentiment": local_summary_row["sentiment"],
    })
    local_summary["model_name"] = local_summary_row.get("model_name", "unknown")

  # derive duration if missing and we have end_time
  if meeting.get("duration") is None and meeting.get("start_time") and meeting.get("end_time"):
    try:
      start_dt = datetime.fromisoformat(meeting["start_time"])
      end_dt = datetime.fromisoformat(meeting["end_time"])
      meeting["duration"] = int((end_dt - start_dt).total_seconds())
    except Exception:
      pass

  return {
    "meeting": meeting,
    "segments": segments,
    "summary": summary,
    "local_summary": local_summary,
  }

