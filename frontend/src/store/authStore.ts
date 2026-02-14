// Zustand store for auth and onboarding state

import { create } from 'zustand'

interface AuthState {
  onboardingComplete: boolean
  setOnboardingComplete: (complete: boolean) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  onboardingComplete:
    localStorage.getItem('onboarding_complete') === 'true',

  setOnboardingComplete: (complete: boolean) => {
    localStorage.setItem('onboarding_complete', String(complete))
    set({ onboardingComplete: complete })
  },
}))
