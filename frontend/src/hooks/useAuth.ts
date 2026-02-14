// Hook for auth / onboarding state

import { useAuthStore } from '../store/authStore'

export function useAuth() {
  const { onboardingComplete, setOnboardingComplete } = useAuthStore()

  return {
    onboardingComplete,
    completeOnboarding: () => setOnboardingComplete(true),
    resetOnboarding: () => setOnboardingComplete(false),
  }
}
