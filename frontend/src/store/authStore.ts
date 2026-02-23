import { create } from 'zustand'
import { apiClient } from '../api/client'

interface User {
  id: string
  username: string
  display_name: string
  role: string
}

interface AuthState {
  token: string | null
  user: User | null
  hasUsers: boolean | null
  onboardingComplete: boolean
  loading: boolean

  login: (username: string, password: string) => Promise<void>
  logout: () => void
  checkAuth: () => Promise<void>
  checkHasUsers: () => Promise<boolean>
  setOnboardingComplete: (complete: boolean) => void
  setAuthFromSetup: (token: string, user: User) => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem('auth_token'),
  user: null,
  hasUsers: null,
  loading: true,
  onboardingComplete: localStorage.getItem('onboarding_complete') === 'true',

  login: async (username: string, password: string) => {
    const { data } = await apiClient.post('/api/auth/login', { username, password })
    localStorage.setItem('auth_token', data.token)
    set({ token: data.token, user: data.user })
  },

  logout: () => {
    localStorage.removeItem('auth_token')
    set({ token: null, user: null })
    window.location.href = '/login'
  },

  checkAuth: async () => {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      set({ token: null, user: null, loading: false })
      return
    }
    try {
      const { data } = await apiClient.get('/api/auth/me')
      set({ token, user: data, loading: false })
    } catch {
      localStorage.removeItem('auth_token')
      set({ token: null, user: null, loading: false })
    }
  },

  checkHasUsers: async () => {
    try {
      const { data } = await apiClient.get('/api/auth/has-users')
      set({ hasUsers: data.has_users })
      return data.has_users
    } catch {
      set({ hasUsers: null })
      return false
    }
  },

  setOnboardingComplete: (complete: boolean) => {
    localStorage.setItem('onboarding_complete', String(complete))
    set({ onboardingComplete: complete })
  },

  setAuthFromSetup: (token: string, user: User) => {
    localStorage.setItem('auth_token', token)
    set({ token, user })
  },
}))
