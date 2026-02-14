// Agentic action types

export interface AgenticAction {
  id: string
  meeting_id: string
  type: 'email_draft' | 'calendar_invite' | 'task_creation'
  title: string
  assignee: string | null
  confidence: number
  draft: EmailDraft | CalendarInviteDraft | Record<string, unknown>
  status: 'pending' | 'approved' | 'dismissed'
  created_at: string
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
