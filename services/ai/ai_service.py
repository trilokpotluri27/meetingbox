import json
import os
from datetime import datetime

import redis
from anthropic import Anthropic

from database import DB_PATH, get_connection


class AIService:
  """
  Consume completed transcripts from SQLite and generate structured
  summaries using Claude, then persist them for the web UI.
  """

  def __init__(self) -> None:
    self.redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
      print("[AI] WARNING: ANTHROPIC_API_KEY is not set; summaries will fail.")

    self.client = Anthropic(api_key=api_key) if api_key else None
    self.model = os.getenv("AI_MODEL", "claude-sonnet-4-20250514")
    self.max_tokens = int(os.getenv("AI_MAX_TOKENS", "2000"))

    print(f"[AI] Service initialized, DB={DB_PATH}")

  # --- Transcript loading ---------------------------------------------

  def _fetch_transcript(self, meeting_id: str) -> str:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
      """
      SELECT segment_num, start_time, text
      FROM segments
      WHERE meeting_id = ?
      ORDER BY segment_num
      """,
      (meeting_id,),
    )
    rows = cur.fetchall()
    conn.close()

    parts: list[str] = []
    for seg_num, start_time, text in rows:
      ts = self._seconds_to_mmss(start_time or 0.0)
      parts.append(f"[{ts}] Segment {seg_num}: {text}")
    return "\n\n".join(parts)

  def _seconds_to_mmss(self, seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

  # --- Claude integration ---------------------------------------------

  def _build_prompt(self, transcript: str) -> str:
    return (
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
      "Transcript:\n\n"
      f"{transcript}"
    )

  def _generate_summary(self, meeting_id: str) -> dict | None:
    if not self.client:
      return None

    transcript = self._fetch_transcript(meeting_id)
    if not transcript:
      print(f"[AI] No transcript found for {meeting_id}")
      return None

    prompt = self._build_prompt(transcript)
    try:
      resp = self.client.messages.create(
        model=self.model,
        max_tokens=self.max_tokens,
        messages=[{"role": "user", "content": prompt}],
      )
      text = resp.content[0].text
    except Exception as exc:
      print(f"[AI] Error calling Claude: {exc}")
      return None

    # handle possible markdown code fences
    if "```json" in text:
      start = text.find("```json") + len("```json")
      end = text.find("```", start)
      json_str = text[start:end].strip()
    else:
      json_str = text.strip()

    try:
      data = json.loads(json_str)
    except json.JSONDecodeError:
      print("[AI] Failed to parse JSON from Claude response")
      return None

    return data

  # --- Persistence -----------------------------------------------------

  def _save_summary(self, meeting_id: str, summary: dict) -> None:
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
        summary.get("summary", ""),
        json.dumps(summary.get("action_items", [])),
        json.dumps(summary.get("decisions", [])),
        json.dumps(summary.get("topics", [])),
        summary.get("sentiment", ""),
        datetime.now().isoformat(),
      ),
    )

    cur.execute(
      """
      UPDATE meetings
      SET status = 'completed', end_time = ?
      WHERE id = ?
      """,
      (datetime.now().isoformat(), meeting_id),
    )

    conn.commit()
    conn.close()

  # --- Event loop ------------------------------------------------------

  def run(self) -> None:
    print("[AI] Service started, waiting for transcription_complete events...")
    pubsub = self.redis_client.pubsub()
    pubsub.subscribe("events")

    for message in pubsub.listen():
      if message["type"] != "message":
        continue
      try:
        event = json.loads(message["data"])
      except json.JSONDecodeError:
        continue

      if event.get("type") != "transcription_complete":
        continue

      meeting_id = event.get("meeting_id")
      if not meeting_id:
        continue

      print(f"[AI] Generating summary for {meeting_id}")
      summary = self._generate_summary(meeting_id)
      if not summary:
        continue

      self._save_summary(meeting_id, summary)

      self.redis_client.publish(
        "events",
        json.dumps(
          {
            "type": "summary_complete",
            "meeting_id": meeting_id,
            "timestamp": datetime.now().isoformat(),
          }
        ),
      )


if __name__ == "__main__":
  service = AIService()
  service.run()

