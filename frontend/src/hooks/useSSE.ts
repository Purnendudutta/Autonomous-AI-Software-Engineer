/**
 * useSSE — Custom hook for consuming Server-Sent Events.
 *
 * Usage:
 *   const { events, connected, error } = useSSE(taskApi.getLogsUrl(taskId))
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import type { AgentLogEvent } from '@/types'

interface UseSSEState {
  events: AgentLogEvent[]
  connected: boolean
  error: string | null
}

export function useSSE(url: string | null): UseSSEState {
  const [events, setEvents] = useState<AgentLogEvent[]>([])
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sourceRef = useRef<EventSource | null>(null)

  const connect = useCallback(() => {
    if (!url) return

    const source = new EventSource(url)
    sourceRef.current = source

    source.onopen = () => {
      setConnected(true)
      setError(null)
    }

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as AgentLogEvent
        // Ignore ping events
        if (data.event_type === 'ping') return
        setEvents((prev) => [...prev, data])
      } catch {
        // Ignore malformed events
      }
    }

    source.onerror = () => {
      setConnected(false)
      setError('Connection to event stream failed')
      source.close()
    }
  }, [url])

  useEffect(() => {
    connect()
    return () => {
      sourceRef.current?.close()
      sourceRef.current = null
    }
  }, [connect])

  return { events, connected, error }
}
