import client from './client'
import type { Integration } from '../types/user'

export interface DeviceCodeResponse {
  session_id: string
  user_code: string
  verification_url: string
  expires_in: number
  interval: number
}

export interface PollResponse {
  status: 'pending' | 'complete' | 'expired' | 'denied' | 'error'
  message?: string
  provider?: string
  email?: string
  interval?: number
}

export const integrationsApi = {
  list: async (): Promise<Integration[]> => {
    const response = await client.get('/api/integrations')
    return response.data
  },

  requestDeviceCode: async (provider: string): Promise<DeviceCodeResponse> => {
    const response = await client.post(`/api/integrations/${provider}/device-code`)
    return response.data
  },

  poll: async (provider: string, sessionId: string): Promise<PollResponse> => {
    const response = await client.post(
      `/api/integrations/${provider}/poll`,
      null,
      { params: { session_id: sessionId } },
    )
    return response.data
  },

  disconnect: async (provider: string): Promise<void> => {
    await client.post(`/api/integrations/${provider}/disconnect`)
  },
}
