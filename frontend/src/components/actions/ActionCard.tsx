import { useState } from 'react'
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
  const [isApproving, setIsApproving] = useState(false)
  const [isDismissing, setIsDismissing] = useState(false)

  const isTerminal = action.status === 'executed' || action.status === 'dismissed'
  const canRetry = action.status === 'delivery_failed'

  const handleExecute = async () => {
    try {
      setIsApproving(true)
      if (action.status === 'pending') {
        await actionsApi.approve(action.id)
      }
      const result = await actionsApi.execute(action.id)
      const ds = result.delivery_status
      if (ds === 'sent_via_gmail') {
        toast.success('Email sent via Gmail!')
      } else if (ds === 'created_via_calendar') {
        toast.success('Calendar event created!')
      } else if (ds === 'gmail_not_connected' || ds === 'calendar_not_connected') {
        toast.success('Action executed. Connect the integration in Settings to auto-deliver.')
      } else if (ds === 'gmail_send_failed' || ds === 'calendar_create_failed') {
        toast.error('Delivery failed. You can retry from this card.')
      } else if (ds === 'already_executed') {
        toast('This action was already executed.')
      } else {
        toast.success('Action executed!')
      }
      onApproved()
    } catch {
      toast.error('Failed to execute action')
    } finally {
      setIsApproving(false)
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

  const renderContent = () => {
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
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">Executed</span>
      case 'dismissed':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">Dismissed</span>
      case 'delivery_failed':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Delivery Failed</span>
      case 'approved':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">Approved</span>
      default:
        return null
    }
  }

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

      {/* Action buttons — only for actionable states */}
      {!isTerminal && (
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
          <button
            onClick={handleDismiss}
            disabled={isDismissing}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            {isDismissing ? 'Dismissing...' : 'Dismiss'}
          </button>
          <button
            onClick={handleExecute}
            disabled={isApproving}
            className="px-6 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            {isApproving ? 'Executing...' : canRetry ? 'Retry Execution' : 'Approve & Execute'}
          </button>
        </div>
      )}
    </div>
  )
}
