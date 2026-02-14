// Onboarding flow — 4-step wizard for first-time setup

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { settingsApi } from '../api/settings'
import toast from 'react-hot-toast'

interface OnboardingStep {
  id: number
  title: string
  description: string
}

const steps: OnboardingStep[] = [
  { id: 1, title: 'Welcome', description: "Let's set up your MeetingBox" },
  { id: 2, title: 'Name Your Device', description: 'Give your MeetingBox a memorable name' },
  { id: 3, title: 'Connect Integrations', description: 'Optional: Connect Gmail and Calendar' },
  { id: 4, title: 'All Set!', description: "You're ready to record your first meeting" },
]

export default function Onboarding() {
  const [currentStep, setCurrentStep] = useState(1)
  const [deviceName, setDeviceName] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const navigate = useNavigate()
  const { completeOnboarding } = useAuth()

  const handleNext = async () => {
    // Save device name on step 2
    if (currentStep === 2 && deviceName.trim()) {
      try {
        setIsSaving(true)
        await settingsApi.setDeviceName(deviceName.trim())
      } catch {
        // Non-blocking — continue even if save fails
        console.warn('Could not save device name (backend may be offline)')
      } finally {
        setIsSaving(false)
      }
    }

    if (currentStep < steps.length) {
      setCurrentStep(currentStep + 1)
    } else {
      completeOnboarding()
      navigate('/dashboard')
    }
  }

  const handleSkip = () => {
    completeOnboarding()
    navigate('/dashboard')
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full mx-auto">

        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            {steps.map((step) => (
              <div
                key={step.id}
                className={`flex-1 h-1 mx-1 rounded transition-colors ${
                  step.id <= currentStep ? 'bg-primary-600' : 'bg-gray-200'
                }`}
              />
            ))}
          </div>
          <p className="text-sm text-gray-500 text-center">
            Step {currentStep} of {steps.length}
          </p>
        </div>

        {/* Step content */}
        <div className="bg-white rounded-lg shadow-lg p-8">

          {/* Step 1: Welcome */}
          {currentStep === 1 && (
            <div className="text-center">
              <div className="w-20 h-20 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <svg className="w-10 h-10 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h1 className="text-3xl font-bold text-gray-900 mb-4">Welcome to MeetingBox</h1>
              <p className="text-lg text-gray-600 mb-8">
                Let&apos;s get you set up in just 2 minutes. You&apos;ll be recording AI-powered meeting notes in no time.
              </p>
            </div>
          )}

          {/* Step 2: Name your device */}
          {currentStep === 2 && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Name Your MeetingBox</h2>
              <p className="text-gray-600 mb-6">
                This name will appear on your network and in the dashboard.
              </p>
              <div className="mb-6">
                <label htmlFor="deviceName" className="block text-sm font-medium text-gray-700 mb-2">
                  Device Name
                </label>
                <input
                  type="text"
                  id="deviceName"
                  value={deviceName}
                  onChange={(e) => setDeviceName(e.target.value)}
                  placeholder="Conference Room A"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                <p className="mt-2 text-sm text-gray-500">
                  Suggestion: Use your room name or location
                </p>
              </div>
            </div>
          )}

          {/* Step 3: Integrations */}
          {currentStep === 3 && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Connect Your Tools (Optional)</h2>
              <p className="text-gray-600 mb-6">
                Connect Gmail and Calendar to enable AI-powered actions. You can skip this and set up later.
              </p>
              <div className="space-y-4">
                {/* Gmail */}
                <div className="border border-gray-200 rounded-lg p-4 hover:border-primary-500 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
                        <svg className="w-6 h-6 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                          <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
                        </svg>
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-900">Gmail</h3>
                        <p className="text-sm text-gray-500">Send AI-drafted emails</p>
                      </div>
                    </div>
                    <button
                      onClick={() => toast('Gmail integration coming soon!')}
                      className="px-4 py-2 text-sm font-medium text-primary-700 bg-primary-50 rounded-lg hover:bg-primary-100"
                    >
                      Connect
                    </button>
                  </div>
                </div>
                {/* Google Calendar */}
                <div className="border border-gray-200 rounded-lg p-4 hover:border-primary-500 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <svg className="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-900">Google Calendar</h3>
                        <p className="text-sm text-gray-500">Auto-schedule meetings</p>
                      </div>
                    </div>
                    <button
                      onClick={() => toast('Calendar integration coming soon!')}
                      className="px-4 py-2 text-sm font-medium text-primary-700 bg-primary-50 rounded-lg hover:bg-primary-100"
                    >
                      Connect
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Complete */}
          {currentStep === 4 && (
            <div className="text-center">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <svg className="w-10 h-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">You&apos;re All Set!</h2>
              <p className="text-gray-600 mb-8">
                Your MeetingBox is ready to use. Press the button on the device to start recording, or use this dashboard to manage your meetings.
              </p>
              <div className="bg-primary-50 border border-primary-200 rounded-lg p-4">
                <p className="text-sm text-primary-800 font-medium mb-2">Quick Tip</p>
                <p className="text-sm text-primary-700">
                  Just press the button on your MeetingBox to start recording. We&apos;ll handle the rest &mdash; transcription, summary, and action items.
                </p>
              </div>
            </div>
          )}

          {/* Navigation buttons */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-gray-200">
            {currentStep > 1 && currentStep < steps.length ? (
              <button onClick={handleSkip} className="text-sm text-gray-500 hover:text-gray-700">
                Skip for now
              </button>
            ) : (
              <div /> /* spacer */
            )}
            <div className="flex space-x-3">
              {currentStep > 1 && (
                <button
                  onClick={() => setCurrentStep(currentStep - 1)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Back
                </button>
              )}
              <button
                onClick={handleNext}
                disabled={isSaving}
                className="px-6 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {isSaving
                  ? 'Saving...'
                  : currentStep === steps.length
                    ? 'Go to Dashboard'
                    : 'Continue'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
