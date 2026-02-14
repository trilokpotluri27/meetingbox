// Meeting detail page — summary, transcript, actions tabs, export, summarize buttons

import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { format } from 'date-fns'
import { meetingsApi } from '../api/meetings'
import { actionsApi } from '../api/actions'
import type { MeetingDetail as MeetingDetailType } from '../types/meeting'
import type { AgenticAction } from '../types/action'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import Modal from '../components/ui/Modal'
import Button from '../components/ui/Button'
import TranscriptView from '../components/meeting/TranscriptView'
import SummaryCard from '../components/meeting/SummaryCard'
import ActionCard from '../components/actions/ActionCard'
import toast from 'react-hot-toast'

type Tab = 'summary' | 'transcript' | 'actions'

export default function MeetingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [meeting, setMeeting] = useState<MeetingDetailType | null>(null)
  const [actions, setActions] = useState<AgenticAction[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<Tab>('summary')
  const [summarizing, setSummarizing] = useState(false)
  const [summarizingLocal, setSummarizingLocal] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const loadMeetingData = useCallback(async () => {
    if (!id) return
    try {
      setLoading(true)
      const meetingData = await meetingsApi.get(id)

      // The backend may return { meeting, segments, summary, local_summary }
      // or may return a flat MeetingDetail — handle both shapes
      const raw = meetingData as unknown as Record<string, unknown>
      const normalized: MeetingDetailType =
        'meeting' in raw
          ? {
              ...(raw.meeting as MeetingDetailType),
              segments: (raw.segments as MeetingDetailType['segments']) ?? [],
              summary: (raw.summary as MeetingDetailType['summary']) ?? null,
              local_summary: (raw.local_summary as MeetingDetailType['local_summary']) ?? null,
            }
          : meetingData

      setMeeting(normalized)

      // Try loading actions (may 404 if endpoint doesn't exist yet)
      try {
        const actionsData = await actionsApi.list(id)
        setActions(actionsData)
      } catch {
        setActions([])
      }
    } catch (error) {
      console.error('Failed to load meeting:', error)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    loadMeetingData()
  }, [loadMeetingData])

  const handleExport = async (fmt: 'pdf' | 'docx' | 'txt') => {
    if (!id) return
    try {
      const blob = await meetingsApi.export(id, fmt)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${meeting?.title || 'meeting'}.${fmt}`
      a.click()
      window.URL.revokeObjectURL(url)
      toast.success(`Exported as ${fmt.toUpperCase()}`)
    } catch {
      toast.error('Export failed')
    }
  }

  const handleSummarize = async () => {
    if (!id) return
    setSummarizing(true)
    try {
      await meetingsApi.summarize(id)
      await loadMeetingData()
      toast.success('Summary generated!')
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? ((err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Summarization failed')
          : 'Summarization failed'
      toast.error(msg)
    } finally {
      setSummarizing(false)
    }
  }

  const handleSummarizeLocal = async () => {
    if (!id) return
    setSummarizingLocal(true)
    try {
      await meetingsApi.summarizeLocal(id)
      await loadMeetingData()
      toast.success('Local summary generated!')
    } catch {
      toast.error('Local summarization failed. Is Ollama running?')
    } finally {
      setSummarizingLocal(false)
    }
  }

  const handleActionApproved = (actionId: string) => {
    setActions(actions.filter((a) => a.id !== actionId))
  }

  const handleDeleteMeeting = async () => {
    if (!id) return
    try {
      setIsDeleting(true)
      await meetingsApi.delete(id)
      toast.success('Meeting deleted')
      navigate('/dashboard')
    } catch {
      toast.error('Failed to delete meeting')
    } finally {
      setIsDeleting(false)
      setShowDeleteConfirm(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="large" />
      </div>
    )
  }

  if (!meeting) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Meeting not found</h2>
        <p className="text-gray-600 mb-6">This meeting may have been deleted or doesn&apos;t exist.</p>
        <button
          onClick={() => navigate('/dashboard')}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          Back to Dashboard
        </button>
      </div>
    )
  }

  const hasTranscript = meeting.segments && meeting.segments.length > 0
  const hasSummary = !!meeting.summary
  const hasLocalSummary = !!meeting.local_summary

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

      {/* Back link */}
      <button
        onClick={() => navigate('/dashboard')}
        className="flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4"
      >
        <svg className="w-5 h-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to Dashboard
      </button>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">{meeting.title}</h1>
          <div className="flex items-center space-x-4 text-sm text-gray-600">
            <span>{format(new Date(meeting.start_time), 'PPpp')}</span>
            {meeting.duration != null && (
              <>
                <span>&bull;</span>
                <span>{Math.floor(meeting.duration / 60)} minutes</span>
              </>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => handleExport('pdf')}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Export PDF
          </button>
          <button
            onClick={() => handleExport('txt')}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Export TXT
          </button>
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="px-4 py-2 text-sm font-medium text-red-700 bg-white border border-red-300 rounded-lg hover:bg-red-50"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Summarize buttons — only when transcript exists and no summary yet */}
      {hasTranscript && (!hasSummary || !hasLocalSummary) && (
        <div className="mb-6 bg-white rounded-lg border border-gray-200 p-4 flex flex-wrap items-center gap-3">
          {!hasSummary && (
            <button
              onClick={handleSummarize}
              disabled={summarizing}
              className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {summarizing ? 'Summarizing...' : 'Summarize with API'}
            </button>
          )}
          {!hasLocalSummary && (
            <button
              onClick={handleSummarizeLocal}
              disabled={summarizingLocal}
              className="px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 disabled:opacity-50"
            >
              {summarizingLocal ? 'Summarizing...' : 'Summarize Locally'}
            </button>
          )}
        </div>
      )}

      {/* Pending actions alert */}
      {actions.length > 0 && (
        <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex">
            <svg className="h-5 w-5 text-yellow-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">
                {actions.length} pending action{actions.length > 1 ? 's' : ''} ready for review
              </h3>
              <p className="mt-1 text-sm text-yellow-700">
                Review and approve the AI-generated actions below.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-8">
          {(['summary', 'transcript', 'actions'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
              {tab === 'actions' && actions.length > 0 && (
                <span className="ml-2 bg-yellow-100 text-yellow-800 py-0.5 px-2 rounded-full text-xs">
                  {actions.length}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'summary' && (
          <>
            <SummaryCard summary={meeting.summary} />
            {/* Show local summary below if it exists */}
            {meeting.local_summary && (
              <div className="mt-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Local Summary</h3>
                <SummaryCard summary={meeting.local_summary} />
              </div>
            )}
          </>
        )}

        {activeTab === 'transcript' && (
          <TranscriptView segments={meeting.segments ?? []} />
        )}

        {activeTab === 'actions' && (
          <div className="space-y-4">
            {actions.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h3 className="mt-2 text-sm font-medium text-gray-900">No pending actions</h3>
                <p className="mt-1 text-sm text-gray-500">
                  All action items have been reviewed or no actions were generated.
                </p>
              </div>
            ) : (
              actions.map((action) => (
                <ActionCard
                  key={action.id}
                  action={action}
                  onApproved={() => handleActionApproved(action.id)}
                />
              ))
            )}
          </div>
        )}
      </div>

      {/* Delete confirmation modal */}
      <Modal
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        title="Delete Meeting"
      >
        <p className="text-sm text-gray-600 mb-2">
          Are you sure you want to delete <strong>{meeting.title}</strong>?
        </p>
        <p className="text-sm text-gray-500 mb-6">
          This will permanently remove the recording, transcript, summary, and all associated actions. This cannot be undone.
        </p>
        <div className="flex justify-end gap-3">
          <Button
            variant="secondary"
            onClick={() => setShowDeleteConfirm(false)}
            disabled={isDeleting}
          >
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleDeleteMeeting}
            isLoading={isDeleting}
          >
            Delete Meeting
          </Button>
        </div>
      </Modal>
    </div>
  )
}
