// Settings API endpoints

import client from './client'

export const settingsApi = {
  // Get current settings
  get: async () => {
    const response = await client.get('/api/settings')
    return response.data
  },

  // Update settings
  update: async (settings: Record<string, unknown>) => {
    const response = await client.patch('/api/settings', settings)
    return response.data
  },

  // Setup device name (onboarding)
  setDeviceName: async (name: string) => {
    const response = await client.post('/api/setup/device-name', { name })
    return response.data
  },
}
