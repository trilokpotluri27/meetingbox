// Zustand store for meeting state management

import { create } from 'zustand'
import type { Meeting } from '../types/meeting'
import { meetingsApi } from '../api/meetings'

interface MeetingState {
  meetings: Meeting[]
  loading: boolean
  error: string | null

  // Actions
  fetchMeetings: () => Promise<void>
  startRecording: () => Promise<string>
  stopRecording: (sessionId?: string) => Promise<void>
  deleteMeeting: (id: string) => Promise<void>
}

export const useMeetingStore = create<MeetingState>((set, get) => ({
  meetings: [],
  loading: false,
  error: null,

  fetchMeetings: async () => {
    set({ loading: true, error: null })
    try {
      const meetings = await meetingsApi.list()
      set({ meetings, loading: false })
    } catch (error) {
      set({ error: 'Failed to fetch meetings', loading: false })
      console.error(error)
    }
  },

  startRecording: async () => {
    try {
      const result = await meetingsApi.start()
      // Refresh meetings list after starting
      get().fetchMeetings()
      return result.session_id
    } catch (error) {
      console.error('Failed to start recording:', error)
      throw error
    }
  },

  stopRecording: async (sessionId?: string) => {
    try {
      await meetingsApi.stop(sessionId)
      // Refresh meetings list after stopping
      get().fetchMeetings()
    } catch (error) {
      console.error('Failed to stop recording:', error)
      throw error
    }
  },

  deleteMeeting: async (id: string) => {
    try {
      await meetingsApi.delete(id)
      set({ meetings: get().meetings.filter((m) => m.id !== id) })
    } catch (error) {
      console.error('Failed to delete meeting:', error)
      throw error
    }
  },
}))
