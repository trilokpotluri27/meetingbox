import os
import sqlite3
from pathlib import Path


DB_PATH = os.getenv("MEETINGBOX_DB_PATH", "/data/transcripts/meetings.db")


def init_database() -> None:
  """
  Initialize the core SQLite schema used by MeetingBox services.

  Tables:
  - meetings: one row per recording session
  - segments: transcript chunks with timestamps
  - summaries: AI-generated summaries and metadata
  """
  db_dir = Path(DB_PATH).parent
  db_dir.mkdir(parents=True, exist_ok=True)

  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()

  cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS meetings (
      id TEXT PRIMARY KEY,
      title TEXT,
      start_time TEXT,
      end_time TEXT,
      duration INTEGER,
      audio_path TEXT,
      status TEXT,
      created_at TEXT
    )
    """
  )

  cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS segments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      meeting_id TEXT,
      segment_num INTEGER,
      start_time REAL,
      end_time REAL,
      text TEXT,
      speaker_id TEXT,
      confidence REAL,
      FOREIGN KEY (meeting_id) REFERENCES meetings(id)
    )
    """
  )

  cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS summaries (
      meeting_id TEXT PRIMARY KEY,
      summary TEXT,
      action_items TEXT,
      decisions TEXT,
      topics TEXT,
      sentiment TEXT,
      generated_at TEXT,
      FOREIGN KEY (meeting_id) REFERENCES meetings(id)
    )
    """
  )

  conn.commit()
  conn.close()


def get_connection() -> sqlite3.Connection:
  """
  Return a new SQLite connection to the shared MeetingBox database.

  Callers are responsible for closing the connection.
  """
  return sqlite3.connect(DB_PATH)

