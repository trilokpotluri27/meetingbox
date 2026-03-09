"""
Actions Routes -- CRUD and execution for meeting action items.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_optional_user
from database import get_connection

logger = logging.getLogger(__name__)

router = APIRouter()

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


class ActionResponse(BaseModel):
    id: str
    meeting_id: str
    type: str
    title: Optional[str]
    assignee: Optional[str]
    confidence: Optional[float]
    draft: Optional[dict]
    status: str
    executed_at: Optional[str]
    created_at: Optional[str]


class ActionUpdateRequest(BaseModel):
    title: Optional[str] = None
    assignee: Optional[str] = None
    draft: Optional[dict] = None


_TYPE_MAP = {
    "email": "email_draft",
    "email_draft": "email_draft",
    "calendar": "calendar_invite",
    "calendar_invite": "calendar_invite",
    "task": "task_creation",
    "task_creation": "task_creation",
    "follow_up": "task_creation",
    "followup": "task_creation",
}


def _normalize_action_type(raw: str) -> str:
    return _TYPE_MAP.get(raw.lower().strip(), "task_creation")


_INTEGRATION_TYPES = {"email_draft", "calendar_invite"}


def extract_actions_from_summary(meeting_id: str, action_items: list) -> list[dict]:
    """Parse action_items from a summary and insert only integration-linked actions."""
    if not action_items:
        return []

    conn = get_connection()
    created = []
    try:
        cur = conn.cursor()
        for item in action_items:
            if isinstance(item, str):
                continue
            elif isinstance(item, dict):
                title = (item.get("task") or item.get("title") or "").strip()
                assignee = item.get("assignee")
                raw_type = item.get("type", "task")
                action_type = _normalize_action_type(raw_type)
                draft = {k: v for k, v in item.items() if k not in ("task", "title", "assignee", "type")}
            else:
                continue

            if action_type not in _INTEGRATION_TYPES or not title:
                continue

            # Avoid duplicates when users run summarize/local-summarize multiple times.
            cur.execute(
                """
                SELECT 1
                FROM actions
                WHERE meeting_id = ?
                  AND type = ?
                  AND lower(trim(title)) = lower(trim(?))
                  AND status IN ('pending', 'approved', 'draft_ready', 'executed')
                LIMIT 1
                """,
                (meeting_id, action_type, title),
            )
            if cur.fetchone():
                continue

            action_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            cur.execute(
                """INSERT INTO actions (id, meeting_id, type, title, assignee, confidence, draft, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
                (action_id, meeting_id, action_type, title, assignee, 1.0, json.dumps(draft), now),
            )
            created.append({
                "id": action_id,
                "meeting_id": meeting_id,
                "type": action_type,
                "title": title,
                "assignee": assignee,
                "status": "pending",
            })
        conn.commit()
    finally:
        conn.close()

    logger.info("Extracted %d integration actions for meeting %s", len(created), meeting_id)
    return created


def _row_to_action(row: dict) -> dict:
    """Convert a DB row to an action response dict, parsing the draft JSON."""
    draft = row.get("draft")
    if isinstance(draft, str):
        try:
            draft = json.loads(draft)
        except (json.JSONDecodeError, TypeError):
            draft = {}
    return {**row, "draft": draft or {}}


@router.get("/meetings/{meeting_id}/actions")
async def list_actions(meeting_id: str, current_user: Optional[dict] = Depends(get_optional_user)):
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM actions WHERE meeting_id = ? ORDER BY created_at",
            (meeting_id,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    return [_row_to_action(r) for r in rows]


@router.patch("/actions/{action_id}")
async def update_action(action_id: str, body: ActionUpdateRequest, current_user: Optional[dict] = Depends(get_optional_user)):
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM actions WHERE id = ?", (action_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Action not found")

        updates = []
        params = []
        if body.title is not None:
            updates.append("title = ?")
            params.append(body.title)
        if body.assignee is not None:
            updates.append("assignee = ?")
            params.append(body.assignee)
        if body.draft is not None:
            updates.append("draft = ?")
            params.append(json.dumps(body.draft))

        if updates:
            params.append(action_id)
            cur.execute(f"UPDATE actions SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

        cur.execute("SELECT * FROM actions WHERE id = ?", (action_id,))
        updated = cur.fetchone()
    finally:
        conn.close()
    return _row_to_action(updated)


@router.post("/actions/{action_id}/approve")
async def approve_action(action_id: str, current_user: Optional[dict] = Depends(get_optional_user)):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, status FROM actions WHERE id = ?", (action_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Action not found")
        cur.execute("UPDATE actions SET status = 'approved' WHERE id = ?", (action_id,))
        conn.commit()
    finally:
        conn.close()
    return {"id": action_id, "status": "approved"}


@router.post("/actions/{action_id}/dismiss")
async def dismiss_action(action_id: str, current_user: Optional[dict] = Depends(get_optional_user)):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM actions WHERE id = ?", (action_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Action not found")
        cur.execute("UPDATE actions SET status = 'dismissed' WHERE id = ?", (action_id,))
        conn.commit()
    finally:
        conn.close()
    return {"id": action_id, "status": "dismissed"}


def _parse_json_from_llm(text: str) -> dict:
    """Best-effort JSON extraction from LLM output."""
    if "```json" in text:
        start = text.find("```json") + len("```json")
        end = text.find("```", start)
        return json.loads(text[start:end].strip())
    if "{" in text:
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        return json.loads(text[json_start:json_end])
    return {"output_type": "text", "content": text, "next_steps": []}


def _get_meeting_context(meeting_id: str) -> str:
    """Fetch meeting title and summary text for prompt enrichment."""
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    try:
        cur = conn.cursor()
        cur.execute("SELECT title, start_time FROM meetings WHERE id = ?", (meeting_id,))
        meeting = cur.fetchone()
        cur.execute("SELECT summary, decisions, action_items FROM summaries WHERE meeting_id = ?", (meeting_id,))
        summary = cur.fetchone()
    finally:
        conn.close()

    parts = []
    if meeting:
        parts.append(f"Meeting title: {meeting.get('title', 'Untitled')}")
        if meeting.get("start_time"):
            parts.append(f"Meeting date: {meeting['start_time']}")
    if summary:
        if summary.get("summary"):
            parts.append(f"Summary: {summary['summary']}")
        for field in ("decisions", "action_items"):
            raw = summary.get(field)
            if raw:
                items = json.loads(raw) if isinstance(raw, str) else raw
                if items:
                    parts.append(f"{field.replace('_', ' ').title()}: {json.dumps(items)}")
    return "\n".join(parts)


def _ask_claude_for_draft(client, action: dict, draft: dict) -> dict:
    """Ask Claude to produce a structured draft for the action."""
    action_type = action["type"]
    meeting_context = _get_meeting_context(action["meeting_id"])

    if action_type == "email_draft":
        output_schema = (
            '{\n'
            '  "output_type": "email",\n'
            '  "to": "recipient@example.com",\n'
            '  "subject": "...",\n'
            '  "body": "...",\n'
            '  "cc": "" \n'
            '}'
        )
    elif action_type == "calendar_invite":
        output_schema = (
            '{\n'
            '  "output_type": "calendar",\n'
            '  "title": "...",\n'
            '  "description": "...",\n'
            '  "attendees": ["email1@example.com"],\n'
            '  "duration_minutes": 30,\n'
            '  "suggested_date": "YYYY-MM-DD",\n'
            '  "suggested_time": "HH:MM"\n'
            '}'
        )
    else:
        output_schema = (
            '{\n'
            '  "output_type": "task",\n'
            '  "content": "...",\n'
            '  "next_steps": ["step1", "step2"]\n'
            '}'
        )

    prompt = (
        f"You are an AI assistant drafting content for an action item from a meeting.\n\n"
        f"=== Meeting Context ===\n{meeting_context}\n\n"
        f"=== Action Details ===\n"
        f"Action type: {action_type}\n"
        f"Title: {action['title']}\n"
        f"Assignee: {action.get('assignee', 'Unassigned')}\n"
        f"Draft/Details: {json.dumps(draft, indent=2)}\n\n"
        f"Use the meeting context above to generate rich, relevant content. "
        f"For MOM emails, include the full summary, key discussion points, decisions, "
        f"and action items in the email body.\n\n"
        f"Generate the structured output. Return ONLY valid JSON:\n{output_schema}"
    )

    model = os.getenv("AI_MODEL", "claude-sonnet-4-20250514")
    resp = client.messages.create(
        model=model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text

    try:
        return _parse_json_from_llm(text)
    except json.JSONDecodeError:
        return {"output_type": "text", "content": text, "next_steps": []}


@router.post("/actions/{action_id}/execute")
async def execute_action(action_id: str, current_user: Optional[dict] = Depends(get_optional_user)):
    """
    Generate a draft for an action (email or calendar). Does NOT send or create
    anything -- the user must review the draft and explicitly trigger delivery
    via the /deliver endpoint.
    """
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM actions WHERE id = ?", (action_id,))
        action = cur.fetchone()
        if not action:
            raise HTTPException(status_code=404, detail="Action not found")
    finally:
        conn.close()

    if action["status"] == "executed":
        return {
            "id": action_id,
            "status": "already_executed",
            "delivery_status": "already_executed",
            "result": {"message": "This action was already executed."},
        }

    client = _get_anthropic_client()
    if not client:
        raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY is not configured.")

    draft = action.get("draft", "{}")
    if isinstance(draft, str):
        try:
            draft = json.loads(draft)
        except (json.JSONDecodeError, TypeError):
            draft = {}

    try:
        result_json = _ask_claude_for_draft(client, action, draft)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Claude API error: {exc}")

    result_json["delivery_status"] = "draft_ready"

    now = datetime.utcnow().isoformat()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE actions SET status = ?, executed_at = ?, draft = ? WHERE id = ?",
            ("draft_ready", now, json.dumps({**draft, "execution_result": result_json}), action_id),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "id": action_id,
        "status": "draft_ready",
        "delivery_status": "draft_ready",
        "result": result_json,
    }


@router.post("/actions/{action_id}/deliver")
async def deliver_action(action_id: str, current_user: Optional[dict] = Depends(get_optional_user)):
    """
    Deliver a previously generated draft -- send email via Gmail or create a
    calendar event. Only allowed when the action status is 'draft_ready'.
    """
    from routes.integrations import get_credentials_for_provider

    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM actions WHERE id = ?", (action_id,))
        action = cur.fetchone()
        if not action:
            raise HTTPException(status_code=404, detail="Action not found")
    finally:
        conn.close()

    if action["status"] == "executed":
        return {
            "id": action_id,
            "status": "already_executed",
            "delivery_status": "already_executed",
            "result": {"message": "This action was already delivered."},
        }

    if action["status"] != "draft_ready":
        raise HTTPException(
            status_code=400,
            detail="Action must be in draft_ready state before delivering. Generate a draft first.",
        )

    draft = action.get("draft", "{}")
    if isinstance(draft, str):
        try:
            draft = json.loads(draft)
        except (json.JSONDecodeError, TypeError):
            draft = {}

    execution_result = draft.get("execution_result")
    if not execution_result:
        raise HTTPException(status_code=400, detail="No draft content found. Generate a draft first.")

    user_id = current_user["id"] if current_user else None
    delivery_status = "draft_only"

    is_email = action["type"] == "email_draft"
    is_calendar = action["type"] == "calendar_invite"

    if is_email and user_id:
        creds = get_credentials_for_provider(user_id, "gmail")
        if creds:
            try:
                from services.gmail import send_email
                gmail_result = send_email(
                    credentials=creds,
                    to=execution_result.get("to", ""),
                    subject=execution_result.get("subject", action["title"]),
                    body=execution_result.get("body", ""),
                    cc=execution_result.get("cc"),
                )
                execution_result["gmail_message_id"] = gmail_result.get("id")
                delivery_status = "sent_via_gmail"
            except Exception as e:
                logger.error("Gmail send failed: %s", e)
                execution_result["gmail_error"] = str(e)
                delivery_status = "gmail_send_failed"
        else:
            delivery_status = "gmail_not_connected"

    elif is_calendar and user_id:
        creds = get_credentials_for_provider(user_id, "calendar")
        if creds:
            try:
                from services.calendar import create_event
                start_date = execution_result.get("suggested_date", "")
                start_time = execution_result.get("suggested_time", "10:00")
                start_iso = f"{start_date}T{start_time}:00" if start_date else None

                cal_result = create_event(
                    credentials=creds,
                    title=execution_result.get("title", action["title"]),
                    start_time=start_iso,
                    duration_minutes=execution_result.get("duration_minutes", 30),
                    description=execution_result.get("description", ""),
                    attendees=execution_result.get("attendees", []),
                )
                execution_result["calendar_event_id"] = cal_result.get("id")
                execution_result["calendar_link"] = cal_result.get("htmlLink")
                delivery_status = "created_via_calendar"
            except Exception as e:
                logger.error("Calendar create failed: %s", e)
                execution_result["calendar_error"] = str(e)
                delivery_status = "calendar_create_failed"
        else:
            delivery_status = "calendar_not_connected"

    execution_result["delivery_status"] = delivery_status

    failed_statuses = {"gmail_send_failed", "calendar_create_failed"}
    not_connected = {"gmail_not_connected", "calendar_not_connected", "draft_only"}
    if delivery_status in failed_statuses:
        action_status = "delivery_failed"
    elif delivery_status in not_connected:
        action_status = "draft_ready"
    else:
        action_status = "executed"

    now = datetime.utcnow().isoformat()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE actions SET status = ?, executed_at = ?, draft = ? WHERE id = ?",
            (action_status, now, json.dumps({**draft, "execution_result": execution_result}), action_id),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "id": action_id,
        "status": action_status,
        "delivery_status": delivery_status,
        "result": execution_result,
    }

