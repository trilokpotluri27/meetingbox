// Root application component — routing, toaster, error boundary

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from './store/authStore'
import Layout from './components/layout/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import Onboarding from './pages/Onboarding'
import Dashboard from './pages/Dashboard'
import MeetingDetail from './pages/MeetingDetail'
import LiveRecording from './pages/LiveRecording'
import Settings from './pages/Settings'
import SystemStatus from './pages/SystemStatus'

export default function App() {
  const onboardingComplete = useAuthStore((s) => s.onboardingComplete)

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Toaster position="top-right" />

        <Routes>
          {/* Onboarding — only accessible if not yet completed */}
          <Route
            path="/onboarding"
            element={
              onboardingComplete ? <Navigate to="/dashboard" /> : <Onboarding />
            }
          />

          {/* Main app (protected by layout + onboarding check) */}
          <Route
            path="/"
            element={
              !onboardingComplete ? (
                <Navigate to="/onboarding" />
              ) : (
                <Layout />
              )
            }
          >
            <Route index element={<Navigate to="/dashboard" />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="meeting/:id" element={<MeetingDetail />} />
            <Route path="live" element={<LiveRecording />} />
            <Route path="settings" element={<Settings />} />
            <Route path="system" element={<SystemStatus />} />
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/dashboard" />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
