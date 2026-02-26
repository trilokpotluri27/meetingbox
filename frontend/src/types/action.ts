// Agentic action types

export interface AgenticAction {
  id: string
  meeting_id: string
  type: 'email_draft' | 'calendar_invite' | 'task_creation'
  title: string
  assignee: string | null
  confidence: number | null
  draft: EmailDraft | CalendarInviteDraft | DraftWithResult | Record<string, unknown>
  status: 'pending' | 'approved' | 'dismissed' | 'executed' | 'draft_ready' | 'delivery_failed'
  executed_at: string | null
  created_at: string | null
}

export interface DraftWithResult {
  execution_result?: Record<string, unknown>
  [key: string]: unknown
}

export interface EmailDraft {
  to: string
  subject: string
  body: string
  context?: string
}

export interface CalendarInviteDraft {
  title: string
  attendees: string[]
  suggested_times: SuggestedTime[]
  duration: number
  description: string
  context?: string
}

export interface SuggestedTime {
  start: string
  end: string
  available: boolean
}
