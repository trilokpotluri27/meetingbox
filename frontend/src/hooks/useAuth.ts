import { useAuthStore } from '../store/authStore'

export function useAuth() {
  const {
    onboardingComplete,
    setOnboardingComplete,
    token,
    user,
    logout,
  } = useAuthStore()

  return {
    isAuthenticated: !!token && !!user,
    user,
    onboardingComplete,
    completeOnboarding: () => setOnboardingComplete(true),
    resetOnboarding: () => setOnboardingComplete(false),
    logout,
  }
}
