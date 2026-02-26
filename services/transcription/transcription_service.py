import json
import logging
import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path

import redis

from database import DB_PATH, init_database, get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("meetingbox.transcription")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")


class TranscriptionService:
  """
  Consume completed recordings, run Whisper.cpp on them, and persist
  structured transcript segments into SQLite.

  Uses the multilingual tiny model (ggml-tiny.bin) for both final
  transcription and live per-segment transcription during recording.
  """

  def __init__(self) -> None:
    self.redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

    init_database()

    self.whisper_bin = "/app/whisper.cpp/build/bin/whisper-cli"
    self.model_path = "/app/whisper.cpp/models/ggml-tiny.bin"
    self.live_model_path = self.model_path

    self._live_enabled = Path(self.live_model_path).exists()
    if self._live_enabled:
      logger.info("Live transcription enabled (tiny multilingual model found)")
    else:
      logger.warning("Live transcription disabled (tiny model not found)")

    logger.info("Service initialized, DB=%s", DB_PATH)

  # --- Whisper wrapper -------------------------------------------------

  def transcribe_with_whisper(self, audio_path: str) -> dict | None:
    logger.info("Processing %s", audio_path)
    path = Path(audio_path)
    if not path.exists():
      logger.error("Audio file not found: %s", audio_path)
      return None

    # Use -of (output-file) to explicitly set output base path (without extension).
    # whisper-cli will create <base>.txt and <base>.srt next to the WAV.
    output_base = str(path.with_suffix(""))  # e.g. /data/audio/recordings/20260212_110606
    txt_path = Path(output_base + ".txt")
    srt_path = Path(output_base + ".srt")

    cmd = [
      self.whisper_bin,
      "-m",
      self.model_path,
      "-f",
      audio_path,
      "-of",
      output_base,
      "-otxt",
      "-osrt",
      "--threads",
      os.getenv("WHISPER_THREADS", "4"),
    ]

    logger.info("Running: %s", " ".join(cmd))

    try:
      result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,
      )
    except subprocess.TimeoutExpired:
      logger.error("Whisper timed out")
      return None

    if result.stdout:
      for line in result.stdout.strip().splitlines()[-10:]:
        logger.debug("whisper stdout: %s", line)
    if result.stderr:
      for line in result.stderr.strip().splitlines()[-10:]:
        logger.debug("whisper stderr: %s", line)
    logger.info("whisper exit code: %d", result.returncode)

    if result.returncode != 0:
      return None

    parent = path.parent
    found_files = sorted(parent.glob(path.stem + ".*"))
    logger.debug("Files matching %s.*: %s", path.stem, [str(f) for f in found_files])

    if not txt_path.exists() or not srt_path.exists():
      logger.error("Expected: %s and %s", txt_path, srt_path)
      return None

    full_text = txt_path.read_text(encoding="utf-8", errors="ignore")
    segments = self._parse_srt(srt_path)

    logger.info("Completed with %d segments", len(segments))
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

  # --- Live transcription (per-segment, using tiny model) ---------------

  def _live_transcribe_segment(self, audio_path: str) -> str | None:
    """Run whisper-cli with the tiny model on a single audio segment.
    Returns the transcribed text, or None on failure."""
    path = Path(audio_path)
    if not path.exists():
      logger.warning("Live: segment file not found: %s", audio_path)
      return None

    output_base = str(path.with_suffix("")) + "_live"
    txt_path = Path(output_base + ".txt")

    cmd = [
      self.whisper_bin,
      "-m", self.live_model_path,
      "-f", audio_path,
      "-of", output_base,
      "-otxt",
      "--no-timestamps",
      "--threads", os.getenv("WHISPER_LIVE_THREADS", "2"),
    ]

    try:
      result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
      logger.warning("Live: whisper timed out on %s", audio_path)
      return None

    if result.returncode != 0:
      return None

    if not txt_path.exists():
      return None

    text = txt_path.read_text(encoding="utf-8", errors="ignore").strip()
    try:
      txt_path.unlink()
    except OSError:
      pass

    return text if text else None

  def _live_segment_listener(self) -> None:
    """Background thread: subscribe to audio_segments and transcribe each one live."""
    logger.info("Live transcription listener started")
    client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
    pubsub = client.pubsub()
    pubsub.subscribe("audio_segments")

    for message in pubsub.listen():
      if message["type"] != "message":
        continue
      try:
        segment = json.loads(message["data"])
      except json.JSONDecodeError:
        continue

      audio_path = segment.get("path")
      session_id = segment.get("session_id")
      if not audio_path:
        continue

      text = self._live_transcribe_segment(audio_path)
      if text:
        logger.info("Live: segment %s -> %s", segment.get("segment_num"), text[:80])
        client.publish(
          "events",
          json.dumps({
            "type": "transcription_update",
            "text": text,
            "session_id": session_id,
            "segment_num": segment.get("segment_num"),
            "timestamp": datetime.now().isoformat(),
          }),
        )

  # --- Persistence -----------------------------------------------------

  def _ensure_meeting_record(self, meeting_id: str, audio_path: str) -> None:
    conn = get_connection()
    try:
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
    finally:
      conn.close()

  def _set_meeting_status(self, meeting_id: str, status: str) -> None:
    conn = get_connection()
    try:
      conn.execute("UPDATE meetings SET status = ? WHERE id = ?", (status, meeting_id))
      conn.commit()
    finally:
      conn.close()

  def _save_transcription(self, meeting_id: str, transcription: dict) -> None:
    conn = get_connection()
    try:
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
      cur.execute("UPDATE meetings SET status = 'transcribed' WHERE id = ?", (meeting_id,))
      conn.commit()
    finally:
      conn.close()

  # --- Event loop ------------------------------------------------------

  def run(self) -> None:
    logger.info("Service started, waiting for events...")

    if self._live_enabled:
      live_thread = threading.Thread(target=self._live_segment_listener, daemon=True)
      live_thread.start()

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

      def set_recording_idle() -> None:
        self.redis_client.set("recording_state", "idle")

      if not meeting_id or not audio_path:
        logger.warning("recording_stopped missing session_id or path (no audio captured?)")
        set_recording_idle()
        continue

      logger.info("Starting transcription for %s", meeting_id)
      self._ensure_meeting_record(meeting_id, audio_path)
      transcription = self.transcribe_with_whisper(audio_path)
      if not transcription:
        self._set_meeting_status(meeting_id, "transcription_failed")
        set_recording_idle()
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
      set_recording_idle()


if __name__ == "__main__":
  service = TranscriptionService()
  service.run()

