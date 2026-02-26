// Agentic actions API endpoints

import client from './client'
import type { AgenticAction } from '../types/action'

export interface ExecuteResult {
  id: string
  status: string
  delivery_status: string
  result: Record<string, unknown>
}

export const actionsApi = {
  list: async (meetingId: string): Promise<AgenticAction[]> => {
    const response = await client.get(`/api/meetings/${meetingId}/actions`)
    return response.data
  },

  approve: async (actionId: string): Promise<void> => {
    await client.post(`/api/actions/${actionId}/approve`)
  },

  dismiss: async (actionId: string): Promise<void> => {
    await client.post(`/api/actions/${actionId}/dismiss`)
  },

  execute: async (actionId: string): Promise<ExecuteResult> => {
    const response = await client.post(`/api/actions/${actionId}/execute`)
    return response.data
  },

  deliver: async (actionId: string): Promise<ExecuteResult> => {
    const response = await client.post(`/api/actions/${actionId}/deliver`)
    return response.data
  },

  update: async (actionId: string, draft: unknown): Promise<AgenticAction> => {
    const response = await client.patch(`/api/actions/${actionId}`, { draft })
    return response.data
  },
}
