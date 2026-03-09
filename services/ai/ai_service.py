import json
import logging
import os
from datetime import datetime

import httpx
import redis

from database import DB_PATH, get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("meetingbox.ai")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "phi3:mini")

# Set USE_LOCAL_LLM=false (and provide ANTHROPIC_API_KEY) to fall back to Claude.
USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "true").lower() not in ("false", "0", "no")


class AIService:
  """
  Consume completed transcripts from SQLite and generate structured
  summaries, then persist them for the web UI.

  Default: uses the local Ollama LLM (phi3:mini or configured LOCAL_LLM_MODEL).
  Fallback: Claude API when USE_LOCAL_LLM=false and ANTHROPIC_API_KEY is set.
  """

  def __init__(self) -> None:
    self.redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

    if USE_LOCAL_LLM:
      logger.info("Summarization mode: LOCAL LLM (%s @ %s)", LOCAL_LLM_MODEL, OLLAMA_HOST)
      self._claude_client = None
    else:
      try:
        from anthropic import Anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
          logger.warning("USE_LOCAL_LLM=false but ANTHROPIC_API_KEY is not set — falling back to local LLM.")
          self._claude_client = None
        else:
          self._claude_client = Anthropic(api_key=api_key)
          self._claude_model = os.getenv("AI_MODEL", "claude-sonnet-4-20250514")
          self._claude_max_tokens = int(os.getenv("AI_MAX_TOKENS", "2000"))
          logger.info("Summarization mode: Claude API (%s)", self._claude_model)
      except ImportError:
        logger.warning("anthropic package not installed — falling back to local LLM.")
        self._claude_client = None

    logger.info("Service initialized, DB=%s", DB_PATH)

  # ------------------------------------------------------------------
  # Shared helpers
  # ------------------------------------------------------------------

  def _fetch_transcript(self, meeting_id: str) -> str:
    conn = get_connection()
    try:
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
    finally:
      conn.close()

    parts: list[str] = []
    for seg_num, start_time, text in rows:
      mins = int((start_time or 0) // 60)
      secs = int((start_time or 0) % 60)
      parts.append(f"[{mins:02d}:{secs:02d}] Segment {seg_num}: {text}")
    return "\n\n".join(parts)

  def _build_prompt(self, transcript: str) -> str:
    return (
      "You are analyzing a meeting transcript. Please provide:\n\n"
      "1. Summary (2-3 sentences)\n"
      "2. Key discussion points (3-5 bullets)\n"
      "3. Decisions made\n"
      "4. Action items with assignees if available. Each action item MUST include a "
      '"type" field with one of these values:\n'
      '   - "email_draft" — for items that require sending an email\n'
      '   - "calendar_invite" — for items that require scheduling a meeting\n'
      '   - "task" — for general to-do items\n'
      '   IMPORTANT: Always include this item:\n'
      '   {"task": "Send MOM of this meeting to all stakeholders", "assignee": null, '
      '"due_date": null, "type": "email_draft"}\n'
      "5. 3-5 topic hashtags\n"
      "6. Overall sentiment (single word or short phrase)\n\n"
      "Return **only** valid JSON with no additional text, in this exact shape:\n"
      '{\n'
      '  "summary": "...",\n'
      '  "discussion_points": ["...", "..."],\n'
      '  "decisions": ["...", "..."],\n'
      '  "action_items": [{"task": "...", "assignee": "...", "due_date": "...", "type": "task"}],\n'
      '  "topics": ["#topic1", "#topic2"],\n'
      '  "sentiment": "Productive"\n'
      "}\n\n"
      f"Transcript:\n\n{transcript}"
    )

  def _parse_json(self, text: str, source: str) -> dict | None:
    if "```json" in text:
      start = text.find("```json") + len("```json")
      end = text.find("```", start)
      json_str = text[start:end].strip()
    else:
      json_str = text.strip()
    try:
      return json.loads(json_str)
    except json.JSONDecodeError:
      logger.error("Failed to parse JSON from %s response: %s", source, json_str[:200])
      return None

  # ------------------------------------------------------------------
  # Local LLM (Ollama)
  # ------------------------------------------------------------------

  def _generate_summary_local(self, meeting_id: str) -> dict | None:
    transcript = self._fetch_transcript(meeting_id)
    if not transcript:
      logger.warning("No transcript found for %s", meeting_id)
      return None

    prompt = self._build_prompt(transcript)
    try:
      resp = httpx.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
          "model": LOCAL_LLM_MODEL,
          "prompt": prompt,
          "stream": False,
          "options": {"temperature": 0.3, "num_predict": 2000},
        },
        timeout=300.0,
      )
      resp.raise_for_status()
      text = resp.json().get("response", "")
    except httpx.ConnectError:
      logger.error("Cannot connect to Ollama at %s — is the container running?", OLLAMA_HOST)
      return None
    except Exception:
      logger.exception("Ollama request failed for %s", meeting_id)
      return None

    return self._parse_json(text, "Ollama")

  def _save_summary_local(self, meeting_id: str, summary: dict) -> None:
    conn = get_connection()
    try:
      cur = conn.cursor()
      cur.execute(
        """
        INSERT OR REPLACE INTO local_summaries
          (meeting_id, summary, action_items, decisions, topics, sentiment, model_name, generated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
          meeting_id,
          summary.get("summary", ""),
          json.dumps(summary.get("action_items", [])),
          json.dumps(summary.get("decisions", [])),
          json.dumps(summary.get("topics", [])),
          summary.get("sentiment", ""),
          LOCAL_LLM_MODEL,
          datetime.now().isoformat(),
        ),
      )
      cur.execute(
        "UPDATE meetings SET status = 'completed', end_time = ? WHERE id = ?",
        (datetime.now().isoformat(), meeting_id),
      )
      conn.commit()
    finally:
      conn.close()

  # ------------------------------------------------------------------
  # Claude fallback
  # ------------------------------------------------------------------

  def _generate_summary_claude(self, meeting_id: str) -> dict | None:
    if not self._claude_client:
      return None

    transcript = self._fetch_transcript(meeting_id)
    if not transcript:
      logger.warning("No transcript found for %s", meeting_id)
      return None

    prompt = self._build_prompt(transcript)
    try:
      resp = self._claude_client.messages.create(
        model=self._claude_model,
        max_tokens=self._claude_max_tokens,
        messages=[{"role": "user", "content": prompt}],
      )
      text = resp.content[0].text
    except Exception:
      logger.exception("Error calling Claude for %s", meeting_id)
      return None

    return self._parse_json(text, "Claude")

  def _save_summary_claude(self, meeting_id: str, summary: dict) -> None:
    conn = get_connection()
    try:
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
        "UPDATE meetings SET status = 'completed', end_time = ? WHERE id = ?",
        (datetime.now().isoformat(), meeting_id),
      )
      conn.commit()
    finally:
      conn.close()

  # ------------------------------------------------------------------
  # Main loop
  # ------------------------------------------------------------------

  def run(self) -> None:
    logger.info("Service started, waiting for transcription_complete events...")
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

      logger.info("Generating summary for %s", meeting_id)

      if USE_LOCAL_LLM or not self._claude_client:
        summary = self._generate_summary_local(meeting_id)
        if summary:
          self._save_summary_local(meeting_id, summary)
      else:
        summary = self._generate_summary_claude(meeting_id)
        if summary:
          self._save_summary_claude(meeting_id, summary)

      if not summary:
        logger.warning("Summary generation failed for %s", meeting_id)
        continue

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
