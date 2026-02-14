// Zustand store for agentic actions state

import { create } from 'zustand'
import type { AgenticAction } from '../types/action'
import { actionsApi } from '../api/actions'

interface ActionState {
  actions: AgenticAction[]
  loading: boolean
  error: string | null

  fetchActions: (meetingId: string) => Promise<void>
  approveAction: (actionId: string) => Promise<void>
  dismissAction: (actionId: string) => Promise<void>
}

export const useActionStore = create<ActionState>((set, get) => ({
  actions: [],
  loading: false,
  error: null,

  fetchActions: async (meetingId: string) => {
    set({ loading: true, error: null })
    try {
      const actions = await actionsApi.list(meetingId)
      set({ actions, loading: false })
    } catch (error) {
      set({ error: 'Failed to fetch actions', loading: false })
      console.error(error)
    }
  },

  approveAction: async (actionId: string) => {
    try {
      await actionsApi.approve(actionId)
      set({ actions: get().actions.filter((a) => a.id !== actionId) })
    } catch (error) {
      console.error('Failed to approve action:', error)
      throw error
    }
  },

  dismissAction: async (actionId: string) => {
    try {
      await actionsApi.dismiss(actionId)
      set({ actions: get().actions.filter((a) => a.id !== actionId) })
    } catch (error) {
      console.error('Failed to dismiss action:', error)
      throw error
    }
  },
}))
