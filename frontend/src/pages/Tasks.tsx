import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  ListTodo,
  Plus,
  Loader2,
  AlertCircle,
  Clock,
  RotateCcw,
  Search,
  Sparkles,
  ArrowRight,
  Trash2,
} from 'lucide-react'
import { repositoryApi, taskApi } from '@/services/api'
import type { Repository, Task, TaskStatus } from '@/types'

const STATUS_BADGES: Record<TaskStatus, string> = {
  pending: 'badge-neutral',
  running: 'badge-info',
  succeeded: 'badge-success',
  partial_success: 'badge-warning',
  failed: 'badge-danger',
  blocked: 'badge-danger',
  cancelled: 'badge-neutral',
}

const BEGINNER_TASK_CATEGORIES = [
  {
    category: '🔢 Math & Number Logic',
    tasks: [
      'Add a factorial(n) function to compute the factorial of a number',
      'Add a fibonacci(n) function to return the n-th Fibonacci number',
      'Add an is_prime(n) function to check whether a number is prime',
      'Add a division function div(a, b) with zero-division check',
    ],
  },
  {
    category: '🔤 Strings & Lists / Arrays',
    tasks: [
      'Add an is_palindrome(text) function to check if a string is a palindrome',
      'Add a reverse_string(text) function to reverse a string',
      'Add a count_vowels(text) function to count vowels in a string',
      'Add a find_max(items) function to find the largest number in a list',
    ],
  },
  {
    category: '📘 Docs, Comments & Tests',
    tasks: [
      'Update README.md with a beginner-friendly project overview and examples',
      'Add unit tests to verify the calculator / utility functions',
    ],
  },
]

export function Tasks() {
  const [repos, setRepos] = useState<Repository[]>([])
  const [selectedRepo, setSelectedRepo] = useState<string>('')
  const [description, setDescription] = useState('')
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<'all' | 'running' | 'succeeded' | 'failed'>('all')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    async function loadData() {
      try {
        const [repoList, taskList] = await Promise.all([
          repositoryApi.list(),
          taskApi.list(),
        ])
        setRepos(repoList)
        setTasks(taskList)
        if (repoList.length > 0) {
          setSelectedRepo(repoList[0].id)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedRepo || !description.trim()) return

    setSubmitting(true)
    setSubmitError(null)

    try {
      const newTask = await taskApi.create({
        repository_id: selectedRepo,
        description: description.trim(),
      })
      setTasks((prev) => [newTask, ...prev])
      setDescription('')
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to create task')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteTask = async (taskId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    e.preventDefault()
    if (!confirm('Are you sure you want to delete this task?')) return
    try {
      await taskApi.delete(taskId)
      setTasks((prev) => prev.filter((t) => t.id !== taskId))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete task')
    }
  }

  const handleClearFailed = async () => {
    if (!confirm('Are you sure you want to clear all failed tasks?')) return
    try {
      await taskApi.clearFailed()
      setTasks((prev) => prev.filter((t) => t.status !== 'failed'))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to clear failed tasks')
    }
  }

  const filteredTasks = tasks.filter((t) => {
    if (statusFilter !== 'all' && t.status !== statusFilter) {
      if (statusFilter === 'running' && t.status !== 'running' && t.status !== 'pending') return false
      if (statusFilter !== 'running' && t.status !== statusFilter) return false
    }
    if (searchQuery.trim()) {
      return (
        t.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.id.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }
    return true
  })

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Engineering Tasks</h1>
        <p className="text-[#8b949e] text-xs mt-0.5">
          Assign autonomous code generation, algorithm implementation, testing, and documentation tasks to the AI agent
        </p>
      </div>

      {/* Create Task Form */}
      <div className="surface p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white flex items-center gap-2">
          <Plus className="w-4 h-4 text-green-400" /> New Autonomous Engineering Task
        </h2>

        {repos.length === 0 && !loading ? (
          <div className="text-xs text-[#8b949e]">
            Please{' '}
            <Link to="/repositories" className="text-blue-400 hover:underline">
              add a repository
            </Link>{' '}
            before assigning tasks.
          </div>
        ) : (
          <form onSubmit={handleCreateTask} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-[#8b949e] mb-1">
                Target Repository
              </label>
              <select
                value={selectedRepo}
                onChange={(e) => setSelectedRepo(e.target.value)}
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-md px-3 py-2 text-xs text-white focus:outline-none focus:border-[#58a6ff]"
              >
                {repos.map((repo) => (
                  <option key={repo.id} value={repo.id}>
                    {repo.owner}/{repo.name} ({repo.default_branch || 'main'})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#8b949e] mb-1">
                Task Description & Specification
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="E.g. Add a factorial(n) function in calculator.py and write unit tests for it..."
                rows={3}
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-md px-3 py-2 text-xs text-white placeholder-[#6e7681] focus:outline-none focus:border-[#58a6ff]"
              />
            </div>

            {/* Quick Task Templates */}
            <div className="space-y-2.5 bg-[#0d1117]/60 p-3.5 rounded-lg border border-[#30363d]">
              <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-yellow-400" />
                Quick Task Templates:
              </span>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {BEGINNER_TASK_CATEGORIES.map((group) => (
                  <div key={group.category} className="space-y-1.5">
                    <p className="text-[11px] font-semibold text-[#8b949e]">{group.category}</p>
                    <div className="flex flex-col gap-1.5">
                      {group.tasks.map((taskText, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => setDescription(taskText)}
                          className="text-left text-[11px] bg-[#161b22] hover:bg-[#21262d] hover:border-[#58a6ff] text-[#c9d1d9] hover:text-white px-2.5 py-1.5 rounded border border-[#30363d] transition-colors"
                        >
                          {taskText}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {submitError && (
              <p className="text-xs text-red-400 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" /> {submitError}
              </p>
            )}

            <div className="pt-1">
              <button
                type="submit"
                disabled={submitting || !description.trim() || !selectedRepo}
                className="btn btn-primary text-xs flex items-center gap-2 py-2 px-4"
              >
                {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                {submitting ? 'Launching Agent Pipeline...' : 'Run Autonomous Agent'}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Task List Header & Filters */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2">
            <ListTodo className="w-4 h-4 text-blue-400" />
            Task History & Runs ({filteredTasks.length})
          </h2>

          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-[#8b949e] absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-[#0d1117] border border-[#30363d] rounded-md pl-8 pr-3 py-1.5 text-xs text-white placeholder-[#6e7681] focus:outline-none focus:border-[#58a6ff] w-48 sm:w-64"
            />
          </div>
        </div>

        {/* Status Filter Tabs */}
        <div className="flex items-center justify-between border-b border-[#30363d] pb-2 text-xs">
          <div className="flex gap-1.5">
            {(['all', 'running', 'succeeded', 'failed'] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setStatusFilter(filter)}
                className={`px-3 py-1 rounded capitalize font-medium transition-colors ${
                  statusFilter === filter
                    ? 'bg-[#21262d] text-white border border-[#30363d]'
                    : 'text-[#8b949e] hover:text-white'
                }`}
              >
                {filter}
              </button>
            ))}
          </div>

          {tasks.some((t) => t.status === 'failed') && (
            <button
              onClick={handleClearFailed}
              className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1.5 hover:underline font-medium px-2 py-1 rounded hover:bg-red-950/20"
            >
              <Trash2 className="w-3.5 h-3.5" /> Clear Failed Tasks
            </button>
          )}
        </div>

        {/* Task Cards */}
        {loading ? (
          <div className="flex items-center gap-2 text-[#8b949e] py-8 justify-center text-xs">
            <Loader2 className="w-4 h-4 animate-spin text-blue-400" /> Loading tasks...
          </div>
        ) : error ? (
          <p className="text-red-400 text-xs">{error}</p>
        ) : filteredTasks.length === 0 ? (
          <div className="surface p-8 text-center text-[#8b949e]">
            <ListTodo className="w-8 h-8 mx-auto mb-2 opacity-40" />
            <p className="text-xs text-white font-medium">No Tasks Found</p>
            <p className="text-[11px] mt-1">Submit a new task above or adjust your search filter.</p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {filteredTasks.map((task) => (
              <div
                key={task.id}
                className="surface p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-[#58a6ff] transition-colors"
              >
                <div className="flex-1 min-w-0 pr-3 space-y-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                        STATUS_BADGES[task.status] || 'badge-neutral'
                      }`}
                    >
                      {task.status}
                    </span>
                    <span className="text-[10px] text-[#8b949e] font-mono">{task.id}</span>
                  </div>
                  <p className="text-xs font-semibold text-white truncate">{task.description}</p>
                  <div className="flex items-center gap-4 text-[10px] text-[#8b949e]">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(task.created_at).toLocaleString()}
                    </span>
                    {task.retry_count > 0 && (
                      <span className="flex items-center gap-1 text-yellow-400 font-medium">
                        <RotateCcw className="w-3 h-3" />
                        Retries: {task.retry_count}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Link
                    to={`/tasks/${task.id}`}
                    className="btn btn-secondary text-xs flex items-center gap-1.5 py-1.5 px-3 whitespace-nowrap"
                  >
                    Open Workspace <ArrowRight className="w-3 h-3" />
                  </Link>
                  <button
                    onClick={(e) => handleDeleteTask(task.id, e)}
                    title="Delete task"
                    className="p-1.5 text-[#8b949e] hover:text-red-400 hover:bg-red-950/30 rounded border border-[#30363d] hover:border-red-800 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
