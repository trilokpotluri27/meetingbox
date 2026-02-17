// WebSocket hook for real-time meeting updates

import { useEffect, useRef, useState, useCallback } from 'react'

export function useWebSocket() {
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null)
  const [readyState, setReadyState] = useState<number>(WebSocket.CONNECTING)
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    const connect = () => {
      // In dev mode (Vite on port 3000), connect directly to the backend.
      // In production, the frontend is served from the backend on the same host.
      const host = window.location.host
      const backendHost = host.includes(':3000')
        ? host.replace(':3000', ':8000')
        : host
      const wsUrl = `ws://${backendHost}/ws`
      ws.current = new WebSocket(wsUrl)

      ws.current.onopen = () => {
        console.log('WebSocket connected')
        setReadyState(WebSocket.OPEN)
      }

      ws.current.onmessage = (event) => {
        setLastMessage(event)
      }

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      ws.current.onclose = () => {
        console.log('WebSocket disconnected')
        setReadyState(WebSocket.CLOSED)

        // Auto-reconnect after 3 seconds
        reconnectTimeout.current = setTimeout(connect, 3000)
      }
    }

    connect()

    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current)
      ws.current?.close()
    }
  }, [])

  const sendMessage = useCallback((message: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(message)
    }
  }, [])

  return { lastMessage, sendMessage, readyState }
}
