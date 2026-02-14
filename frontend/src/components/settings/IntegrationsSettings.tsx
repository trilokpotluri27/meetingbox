// Integrations settings — connect / disconnect Gmail, Calendar, etc.

import { useState, useEffect } from 'react'
import { integrationsApi } from '../../api/integrations'
import type { Integration } from '../../types/user'
import LoadingSpinner from '../ui/LoadingSpinner'
import toast from 'react-hot-toast'

export default function IntegrationsSettings() {
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loading, setLoading] = useState(true)

  const loadIntegrations = async () => {
    try {
      const data = await integrationsApi.list()
      setIntegrations(data)
    } catch {
      // API may not exist yet — show empty state
      setIntegrations([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadIntegrations()
  }, [])

  const handleConnect = async (integrationId: string) => {
    try {
      const authUrl = await integrationsApi.getAuthUrl(integrationId)
      window.location.href = authUrl
    } catch {
      toast.error('Failed to connect')
    }
  }

  const handleDisconnect = async (integrationId: string) => {
    try {
      await integrationsApi.disconnect(integrationId)
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

  if (integrations.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 text-center">
        <p className="text-gray-500">
          No integrations available yet. Gmail and Calendar integrations will appear here once the backend supports them.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {integrations.map((integration) => (
        <div
          key={integration.id}
          className="bg-white rounded-lg border border-gray-200 p-6"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 rounded-lg bg-gray-100 flex items-center justify-center text-2xl">
                {integration.icon || '🔗'}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{integration.name}</h3>
                <p className="text-sm text-gray-600">{integration.description}</p>
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
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700"
              >
                Connect
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
