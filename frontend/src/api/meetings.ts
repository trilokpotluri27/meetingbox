// Meetings API endpoints

import client from './client'
import type { Meeting, MeetingDetail } from '../types/meeting'

export const meetingsApi = {
  // Get all meetings
  list: async (params?: {
    limit?: number
    offset?: number
    status?: string
  }): Promise<Meeting[]> => {
    const response = await client.get('/api/meetings/', { params })
    return response.data
  },

  // Get single meeting with full details
  get: async (id: string): Promise<MeetingDetail> => {
    const response = await client.get(`/api/meetings/${id}`)
    return response.data
  },

  // Start new recording
  start: async (): Promise<{ session_id: string; status: string }> => {
    const response = await client.post('/api/meetings/start')
    return response.data
  },

  // Stop recording
  stop: async (sessionId?: string): Promise<{ status: string }> => {
    if (sessionId) {
      const response = await client.post(`/api/meetings/${sessionId}/stop`)
      return response.data
    }
    const response = await client.post('/api/meetings/stop')
    return response.data
  },

  // Get recording status
  getRecordingStatus: async (): Promise<{
    state: string
    session_id: string | null
  }> => {
    const response = await client.get('/api/meetings/recording-status')
    return response.data
  },

  // Reset stuck recording state
  resetRecordingState: async (): Promise<void> => {
    await client.post('/api/meetings/reset-recording-state')
  },

  // Upload audio from browser mic
  uploadAudio: async (blob: Blob): Promise<void> => {
    const form = new FormData()
    form.append('file', blob, 'recording.webm')
    await client.post('/api/meetings/upload-audio', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // Update meeting
  update: async (id: string, updates: Partial<Meeting>): Promise<Meeting> => {
    const response = await client.patch(`/api/meetings/${id}`, updates)
    return response.data
  },

  // Delete meeting
  delete: async (id: string): Promise<void> => {
    await client.delete(`/api/meetings/${id}`)
  },

  // Summarize with API (Claude)
  summarize: async (id: string): Promise<void> => {
    await client.post(`/api/meetings/${id}/summarize`)
  },

  // Summarize locally (Ollama)
  summarizeLocal: async (id: string): Promise<void> => {
    await client.post(`/api/meetings/${id}/summarize-local`)
  },

  // Export meeting to file
  export: async (id: string, format: 'pdf' | 'docx' | 'txt'): Promise<Blob> => {
    const response = await client.get(`/api/meetings/${id}/export/${format}`, {
      responseType: 'blob',
    })
    return response.data
  },

  // Email summary to recipients
  emailSummary: async (id: string, recipients: string[]): Promise<void> => {
    await client.post(`/api/meetings/${id}/email`, { recipients })
  },
}
