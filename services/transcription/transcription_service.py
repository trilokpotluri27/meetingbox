import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import redis

from database import DB_PATH, init_database, get_connection


class TranscriptionService:
  """
  Consume completed recordings, run Whisper.cpp on them, and persist
  structured transcript segments into SQLite.
  """

  def __init__(self) -> None:
    self.redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

    # ensure DB schema exists
    init_database()

    # whisper.cpp paths inside this container
    self.whisper_bin = "/app/whisper.cpp/main"
    self.model_path = "/app/whisper.cpp/models/ggml-medium.en.bin"

    print(f"[Transcription] Service initialized, DB={DB_PATH}")

  # --- Whisper wrapper -------------------------------------------------

  def transcribe_with_whisper(self, audio_path: str) -> dict | None:
    print(f"[Transcription] Processing {audio_path}")
    base = Path(audio_path).with_suffix("")
    txt_path = base.with_suffix(".txt")
    srt_path = base.with_suffix(".srt")

    cmd = [
      self.whisper_bin,
      "-m",
      self.model_path,
      "-f",
      audio_path,
      "--output-txt",
      "--output-srt",
      "--language",
      "en",
      "--threads",
      os.getenv("WHISPER_THREADS", "4"),
    ]

    try:
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,
      )
    except subprocess.TimeoutExpired:
      print("[Transcription] Whisper timed out")
      return None

    if result.returncode != 0:
      print(f"[Transcription] Whisper error: {result.stderr}")
      return None

    if not txt_path.exists() or not srt_path.exists():
      print("[Transcription] Expected output files not found")
      return None

    full_text = txt_path.read_text(encoding="utf-8", errors="ignore")
    segments = self._parse_srt(srt_path)

    print(f"[Transcription] Completed with {len(segments)} segments")
    return {"full_text": full_text, "segments": segments}

  def _parse_srt(self, path: Path) -> list[dict]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    blocks = content.strip().split("\n\n")
    segments: list[dict] = []

    for block in blocks:
      lines = block.splitlines()
      if len(lines) < 3:
        continue
      try:
        num = int(lines[0])
      except ValueError:
        continue

      timestamp_line = lines[1]
      try:
        start_str, end_str = timestamp_line.split(" --> ")
      except ValueError:
        continue

      start_sec = self._srt_time_to_seconds(start_str)
      end_sec = self._srt_time_to_seconds(end_str)
      text = "\n".join(lines[2:]).strip()

      segments.append(
        {
          "segment_num": num,
          "start_time": start_sec,
          "end_time": end_sec,
          "text": text,
        }
      )
    return segments

  def _srt_time_to_seconds(self, ts: str) -> float:
    # format HH:MM:SS,mmm
    hh, mm, rest = ts.replace(",", ".").split(":")
    return int(hh) * 3600 + int(mm) * 60 + float(rest)

  # --- Persistence -----------------------------------------------------

  def _ensure_meeting_record(self, meeting_id: str, audio_path: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
      """
      INSERT OR IGNORE INTO meetings
        (id, title, start_time, audio_path, status, created_at)
      VALUES (?, ?, ?, ?, ?, ?)
      """,
      (
        meeting_id,
        f"Meeting {meeting_id}",
        datetime.now().isoformat(),
        audio_path,
        "transcribing",
        datetime.now().isoformat(),
      ),
    )
    conn.commit()
    conn.close()

  def _save_transcription(self, meeting_id: str, transcription: dict) -> None:
    conn = get_connection()
    cur = conn.cursor()

    for seg in transcription["segments"]:
      cur.execute(
        """
        INSERT INTO segments
          (meeting_id, segment_num, start_time, end_time, text)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
          meeting_id,
          seg["segment_num"],
          seg["start_time"],
          seg["end_time"],
          seg["text"],
        ),
      )

    cur.execute(
      """
      UPDATE meetings
      SET status = 'transcribed'
      WHERE id = ?
      """,
      (meeting_id,),
    )

    conn.commit()
    conn.close()

  # --- Event loop ------------------------------------------------------

  def run(self) -> None:
    print("[Transcription] Service started, waiting for events...")
    pubsub = self.redis_client.pubsub()
    pubsub.subscribe("events")

    for message in pubsub.listen():
      if message["type"] != "message":
        continue

      try:
        event = json.loads(message["data"])
      except json.JSONDecodeError:
        continue

      if event.get("type") != "recording_stopped":
        continue

      meeting_id = event.get("session_id")
      audio_path = event.get("path")
      if not meeting_id or not audio_path:
        continue

      print(f"[Transcription] Starting transcription for {meeting_id}")
      self._ensure_meeting_record(meeting_id, audio_path)
      transcription = self.transcribe_with_whisper(audio_path)
      if not transcription:
        continue

      self._save_transcription(meeting_id, transcription)

      self.redis_client.publish(
        "events",
        json.dumps(
          {
            "type": "transcription_complete",
            "meeting_id": meeting_id,
            "timestamp": datetime.now().isoformat(),
          }
        ),
      )


if __name__ == "__main__":
  service = TranscriptionService()
  service.run()

