// Integrations API endpoints (Gmail, Calendar, etc.)

import client from './client'
import type { Integration } from '../types/user'

export const integrationsApi = {
  // List available integrations
  list: async (): Promise<Integration[]> => {
    const response = await client.get('/api/integrations')
    return response.data
  },

  // Get OAuth authorization URL for an integration
  getAuthUrl: async (integrationId: string): Promise<string> => {
    const response = await client.get(
      `/api/integrations/${integrationId}/auth-url`
    )
    return response.data.url
  },

  // Disconnect an integration
  disconnect: async (integrationId: string): Promise<void> => {
    await client.post(`/api/integrations/${integrationId}/disconnect`)
  },

  // Handle OAuth callback
  handleCallback: async (
    integrationId: string,
    code: string
  ): Promise<void> => {
    await client.post(`/api/integrations/${integrationId}/callback`, { code })
  },
}
