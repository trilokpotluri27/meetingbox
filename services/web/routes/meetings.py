from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_connection


router = APIRouter()


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
  decisions: list[str]
  topics: list[str]
  sentiment: str


class MeetingDetail(BaseModel):
  meeting: MeetingResponse
  segments: List[TranscriptSegment]
  summary: Optional[MeetingSummary]


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
    import json

    summary = {
      "summary": summary_row["summary"],
      "action_items": json.loads(summary_row["action_items"] or "[]"),
      "decisions": json.loads(summary_row["decisions"] or "[]"),
      "topics": json.loads(summary_row["topics"] or "[]"),
      "sentiment": summary_row["sentiment"],
    }

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
  }

