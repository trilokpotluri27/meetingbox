import { useState, useEffect, useCallback, useRef } from 'react'
import { apiClient } from '../api/client'
import type { SystemInfo } from '../types/user'
import LoadingSpinner from '../components/ui/LoadingSpinner'

export default function SystemStatus() {
  const [info, setInfo] = useState<SystemInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = useCallback(async () => {
    try {
      const res = await apiClient.get<{ system: SystemInfo }>('/api/system/status')
      setInfo(res.data.system)
      setError(null)
    } catch {
      setError('Could not reach the backend. Make sure it is running.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    intervalRef.current = setInterval(load, 5000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [load])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="large" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">System Status</h1>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          <p>{error}</p>
          <button
            onClick={() => { setLoading(true); load() }}
            className="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!info) return null

  const stats = [
    {
      label: 'CPU',
      value: `${info.cpu_percent.toFixed(1)}%`,
      percent: info.cpu_percent,
      color: info.cpu_percent > 80 ? 'bg-red-500' : info.cpu_percent > 50 ? 'bg-yellow-500' : 'bg-green-500',
    },
    {
      label: 'Memory',
      value: `${info.memory_percent.toFixed(1)}% (${info.memory_used_gb.toFixed(1)} / ${info.memory_total_gb.toFixed(1)} GB)`,
      percent: info.memory_percent,
      color: info.memory_percent > 80 ? 'bg-red-500' : info.memory_percent > 50 ? 'bg-yellow-500' : 'bg-green-500',
    },
    {
      label: 'Disk',
      value: `${info.disk_percent.toFixed(1)}% (${info.disk_used_gb.toFixed(1)} / ${info.disk_total_gb.toFixed(1)} GB)`,
      percent: info.disk_percent,
      color: info.disk_percent > 80 ? 'bg-red-500' : info.disk_percent > 50 ? 'bg-yellow-500' : 'bg-green-500',
    },
  ]

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">System Status</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {stats.map((stat) => (
          <div key={stat.label} className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
                {stat.label}
              </h3>
            </div>
            <p className="text-lg font-semibold text-gray-900 mb-3">{stat.value}</p>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${stat.color}`}
                style={{ width: `${Math.min(stat.percent, 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
