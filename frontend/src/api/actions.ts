// Agentic actions API endpoints

import client from './client'
import type { AgenticAction } from '../types/action'

export const actionsApi = {
  // List actions for a meeting
  list: async (meetingId: string): Promise<AgenticAction[]> => {
    const response = await client.get(`/api/meetings/${meetingId}/actions`)
    return response.data
  },

  // Approve and execute action
  approve: async (actionId: string): Promise<void> => {
    await client.post(`/api/actions/${actionId}/approve`)
  },

  // Dismiss action
  dismiss: async (actionId: string): Promise<void> => {
    await client.post(`/api/actions/${actionId}/dismiss`)
  },

  // Update action draft before approving
  update: async (actionId: string, draft: unknown): Promise<AgenticAction> => {
    const response = await client.patch(`/api/actions/${actionId}`, { draft })
    return response.data
  },
}
