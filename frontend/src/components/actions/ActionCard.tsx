import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { actionsApi } from '../../api/actions'
import type { AgenticAction } from '../../types/action'
import EmailDraft from './EmailDraft'
import CalendarInvite from './CalendarInvite'
import toast from 'react-hot-toast'

interface ActionCardProps {
  action: AgenticAction
  onApproved: () => void
}

export default function ActionCard({ action, onApproved }: ActionCardProps) {
  const navigate = useNavigate()
  const [isGenerating, setIsGenerating] = useState(false)
  const [isDelivering, setIsDelivering] = useState(false)
  const [isDismissing, setIsDismissing] = useState(false)
  const [draftResult, setDraftResult] = useState<Record<string, unknown> | null>(() => {
    const d = action.draft as Record<string, unknown> | undefined
    return (d?.execution_result as Record<string, unknown>) ?? null
  })

  const isTerminal = action.status === 'executed' || action.status === 'dismissed'
  const isDraftReady = action.status === 'draft_ready' || draftResult !== null
  const canRetry = action.status === 'delivery_failed'

  const handleGenerateDraft = async () => {
    try {
      setIsGenerating(true)
      if (action.status === 'pending') {
        await actionsApi.approve(action.id)
      }
      const result = await actionsApi.execute(action.id)
      setDraftResult(result.result)
      toast.success('Draft generated! Review it below.')
      onApproved()
    } catch {
      toast.error('Failed to generate draft')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleDeliver = async () => {
    try {
      setIsDelivering(true)
      const result = await actionsApi.deliver(action.id)
      const ds = result.delivery_status

      if (ds === 'sent_via_gmail') {
        toast.success('Email sent via Gmail!')
      } else if (ds === 'created_via_calendar') {
        toast.success('Calendar event created!')
      } else if (ds === 'gmail_not_connected' || ds === 'calendar_not_connected') {
        toast.error('Integration not connected. Redirecting to Settings...')
        navigate('/settings')
        return
      } else if (ds === 'gmail_send_failed' || ds === 'calendar_create_failed') {
        toast.error('Delivery failed. You can retry.')
        return
      }
      onApproved()
    } catch {
      toast.error('Failed to deliver')
    } finally {
      setIsDelivering(false)
    }
  }

  const handleDismiss = async () => {
    try {
      setIsDismissing(true)
      await actionsApi.dismiss(action.id)
      toast.success('Action dismissed')
      onApproved()
    } catch {
      toast.error('Failed to dismiss action')
    } finally {
      setIsDismissing(false)
    }
  }

  const renderDraftPreview = () => {
    if (!draftResult) return null

    if (action.type === 'email_draft') {
      return (
        <EmailDraft
          draft={{
            to: (draftResult.to as string) || '',
            subject: (draftResult.subject as string) || '',
            body: (draftResult.body as string) || '',
            context: draftResult.context as string | undefined,
          }}
        />
      )
    }

    if (action.type === 'calendar_invite') {
      return (
        <CalendarInvite
          draft={{
            title: (draftResult.title as string) || '',
            attendees: (draftResult.attendees as string[]) || [],
            suggested_times: [],
            duration: (draftResult.duration_minutes as number) || 30,
            description: (draftResult.description as string) || '',
            context: draftResult.context as string | undefined,
          }}
        />
      )
    }

    return (
      <div className="p-4 bg-gray-50 rounded-lg">
        <pre className="text-sm text-gray-700 whitespace-pre-wrap">
          {JSON.stringify(draftResult, null, 2)}
        </pre>
      </div>
    )
  }

  const renderContent = () => {
    if (isDraftReady && draftResult) {
      return renderDraftPreview()
    }

    switch (action.type) {
      case 'email_draft':
        return <EmailDraft draft={action.draft as { to: string; subject: string; body: string; context?: string }} />
      case 'calendar_invite':
        return <CalendarInvite draft={action.draft as { title: string; attendees: string[]; suggested_times: { start: string; end: string; available: boolean }[]; duration: number; description: string; context?: string }} />
      default:
        return (
          <div className="p-4 bg-gray-50 rounded-lg">
            <pre className="text-sm text-gray-700 whitespace-pre-wrap">
              {JSON.stringify(action.draft, null, 2)}
            </pre>
          </div>
        )
    }
  }

  const statusBadge = () => {
    switch (action.status) {
      case 'executed':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">Sent</span>
      case 'dismissed':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">Dismissed</span>
      case 'delivery_failed':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Delivery Failed</span>
      case 'draft_ready':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">Draft Ready</span>
      case 'approved':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">Approved</span>
      default:
        return null
    }
  }

  const deliverLabel = action.type === 'calendar_invite' ? 'Add to Calendar' : 'Send Email'

  return (
    <div className={`bg-white rounded-lg border overflow-hidden ${isTerminal ? 'border-gray-100 opacity-75' : 'border-gray-200'}`}>
      {/* Header */}
      <div className="px-6 py-4 bg-primary-50 border-b border-primary-100">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{action.title}</h3>
            {action.assignee && (
              <p className="text-sm text-gray-600 mt-1">For: {action.assignee}</p>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800">
              {action.type.replaceAll('_', ' ')}
            </span>
            {statusBadge()}
            {action.confidence != null && (
              <span className="text-xs text-gray-500">
                {Math.round(action.confidence * 100)}% confidence
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-4">{renderContent()}</div>

      {/* Action buttons */}
      {!isTerminal && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
          <button
            onClick={handleDismiss}
            disabled={isDismissing}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            {isDismissing ? 'Dismissing...' : 'Dismiss'}
          </button>

          <div className="flex items-center gap-2">
            {isDraftReady && draftResult ? (
              <button
                onClick={handleDeliver}
                disabled={isDelivering}
                className="px-6 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                {isDelivering ? 'Sending...' : deliverLabel}
              </button>
            ) : (
              <button
                onClick={handleGenerateDraft}
                disabled={isGenerating}
                className="px-6 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {isGenerating ? 'Generating...' : canRetry ? 'Retry Draft' : 'Create Draft'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
