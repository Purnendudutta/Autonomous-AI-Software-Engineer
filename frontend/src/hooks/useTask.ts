/**
 * useTask — Hook for polling task status and loading task data.
 */

import { useCallback, useEffect, useState } from 'react'
import { taskApi } from '@/services/api'
import type { Task, TaskStatusResponse } from '@/types'

const TERMINAL_STATUSES = new Set(['succeeded', 'partial_success', 'failed', 'blocked', 'cancelled'])
const POLL_INTERVAL_MS = 3000

interface UseTaskState {
  task: Task | null
  status: TaskStatusResponse | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useTask(taskId: string | null): UseTaskState {
  const [task, setTask] = useState<Task | null>(null)
  const [status, setStatus] = useState<TaskStatusResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchTask = useCallback(async () => {
    if (!taskId) return
    setLoading(true)
    try {
      const [t, s] = await Promise.all([
        taskApi.get(taskId),
        taskApi.getStatus(taskId),
      ])
      setTask(t)
      setStatus(s)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load task')
    } finally {
      setLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    fetchTask()
  }, [fetchTask])

  // Poll while task is running
  useEffect(() => {
    if (!taskId || !task) return
    if (TERMINAL_STATUSES.has(task.status)) return

    const interval = setInterval(fetchTask, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [taskId, task, fetchTask])

  return { task, status, loading, error, refetch: fetchTask }
}
