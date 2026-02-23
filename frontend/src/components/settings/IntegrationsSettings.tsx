import { useState, useEffect, useRef, useCallback } from 'react'
import { integrationsApi } from '../../api/integrations'
import type { DeviceCodeResponse, PollResponse } from '../../api/integrations'
import type { Integration } from '../../types/user'
import LoadingSpinner from '../ui/LoadingSpinner'
import toast from 'react-hot-toast'

interface ActiveSession {
  provider: string
  session_id: string
  user_code: string
  verification_url: string
  interval: number
}

export default function IntegrationsSettings() {
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loading, setLoading] = useState(true)
  const [activeSession, setActiveSession] = useState<ActiveSession | null>(null)
  const [connecting, setConnecting] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const loadIntegrations = useCallback(async () => {
    try {
      const data = await integrationsApi.list()
      setIntegrations(data)
    } catch {
      setIntegrations([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadIntegrations()
    return () => {
      if (pollRef.current) clearTimeout(pollRef.current)
    }
  }, [loadIntegrations])

  const startPolling = useCallback((provider: string, sessionId: string, interval: number) => {
    const poll = async () => {
      try {
        const result: PollResponse = await integrationsApi.poll(provider, sessionId)

        if (result.status === 'complete') {
          toast.success(`${provider === 'gmail' ? 'Gmail' : 'Google Calendar'} connected as ${result.email}!`)
          setActiveSession(null)
          setConnecting(null)
          loadIntegrations()
          return
        }

        if (result.status === 'expired' || result.status === 'denied' || result.status === 'error') {
          toast.error(result.message || 'Connection failed')
          setActiveSession(null)
          setConnecting(null)
          return
        }

        const nextInterval = (result.interval ?? interval) * 1000
        pollRef.current = setTimeout(poll, nextInterval)
      } catch {
        toast.error('Polling error. Please try again.')
        setActiveSession(null)
        setConnecting(null)
      }
    }

    pollRef.current = setTimeout(poll, interval * 1000)
  }, [loadIntegrations])

  const handleConnect = async (provider: string) => {
    setConnecting(provider)
    try {
      const data: DeviceCodeResponse = await integrationsApi.requestDeviceCode(provider)
      setActiveSession({
        provider,
        session_id: data.session_id,
        user_code: data.user_code,
        verification_url: data.verification_url,
        interval: data.interval,
      })
      startPolling(provider, data.session_id, data.interval)
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Failed to start connection'
      toast.error(msg)
      setConnecting(null)
    }
  }

  const handleCancel = () => {
    if (pollRef.current) clearTimeout(pollRef.current)
    setActiveSession(null)
    setConnecting(null)
  }

  const handleDisconnect = async (provider: string) => {
    try {
      await integrationsApi.disconnect(provider)
      toast.success('Disconnected')
      loadIntegrations()
    } catch {
      toast.error('Failed to disconnect')
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Device code authorization modal */}
      {activeSession && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">
            Connect {activeSession.provider === 'gmail' ? 'Gmail' : 'Google Calendar'}
          </h3>
          <p className="text-blue-800 mb-4">
            Open the link below on any device and enter the code to authorize:
          </p>
          <div className="flex flex-col items-center space-y-4 mb-4">
            <a
              href={activeSession.verification_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 underline font-medium text-lg hover:text-blue-800"
            >
              {activeSession.verification_url}
            </a>
            <div className="bg-white border-2 border-blue-300 rounded-xl px-8 py-4 shadow-sm">
              <span className="font-mono text-3xl font-bold tracking-widest text-gray-900">
                {activeSession.user_code}
              </span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <p className="text-sm text-blue-600 flex items-center">
              <svg className="w-4 h-4 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Waiting for authorization...
            </p>
            <button
              onClick={handleCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {integrations.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-6 text-center">
          <p className="text-gray-500">
            No integrations available. Ensure the backend is running and Google OAuth credentials are configured.
          </p>
        </div>
      ) : (
        integrations.map((integration) => (
          <div
            key={integration.id}
            className="bg-white rounded-lg border border-gray-200 p-6"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 rounded-lg bg-gray-100 flex items-center justify-center text-2xl">
                  {integration.id === 'gmail' ? (
                    <svg className="w-7 h-7 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                      <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
                    </svg>
                  ) : (
                    <svg className="w-7 h-7 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">{integration.name}</h3>
                  <p className="text-sm text-gray-600">{integration.description}</p>
                  {integration.connected && integration.email && (
                    <p className="text-xs text-green-600 mt-1">Connected as {integration.email}</p>
                  )}
                </div>
              </div>

              {integration.connected ? (
                <div className="flex items-center space-x-3">
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-green-100 text-green-800">
                    Connected
                  </span>
                  <button
                    onClick={() => handleDisconnect(integration.id)}
                    className="px-4 py-2 text-sm font-medium text-red-700 bg-red-50 rounded-lg hover:bg-red-100"
                  >
                    Disconnect
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => handleConnect(integration.id)}
                  disabled={connecting !== null}
                  className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50"
                >
                  {connecting === integration.id ? 'Starting...' : 'Connect'}
                </button>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
