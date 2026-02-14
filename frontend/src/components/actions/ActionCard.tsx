// Card displaying a single agentic action with approve / dismiss / edit controls

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

  const handleApprove = async () => {
    try {
      setIsApproving(true)
      await actionsApi.approve(action.id)
      toast.success('Action approved and executed!')
      onApproved()
    } catch {
      toast.error('Failed to approve action')
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

  // Render the action content based on its type
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

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
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
              {action.type.replace('_', ' ')}
            </span>
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
      <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
        <button
          onClick={handleDismiss}
          disabled={isDismissing}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
        >
          {isDismissing ? 'Dismissing...' : 'Dismiss'}
        </button>
        <button
          onClick={handleApprove}
          disabled={isApproving}
          className="px-6 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50"
        >
          {isApproving ? 'Approving...' : 'Approve & Execute'}
        </button>
      </div>
    </div>
  )
}
