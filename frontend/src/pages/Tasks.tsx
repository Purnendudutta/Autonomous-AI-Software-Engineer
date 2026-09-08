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

const PROMPT_PRESETS = [
  'Fix token expiration bug in authentication service',
  'Add healthcheck endpoint with system diagnostics',
  'Implement input validation and error handling for user routes',
  'Refactor database query to optimize response times',
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
          Assign autonomous debugging, feature implementation, and refactoring tasks to the AI agent
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
          <form onSubmit={handleCreateTask} className="space-y-3">
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
                Task Description & Instructions
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="E.g. Fix token expiration handling in auth service and add regression test..."
                rows={3}
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-md px-3 py-2 text-xs text-white placeholder-[#6e7681] focus:outline-none focus:border-[#58a6ff]"
              />
            </div>

            {/* Prompt presets */}
            <div className="space-y-1.5">
              <span className="text-[11px] text-[#8b949e] flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-yellow-400" /> Quick Task Templates:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {PROMPT_PRESETS.map((p, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setDescription(p)}
                    className="text-[10px] bg-[#21262d] hover:bg-[#30363d] text-[#c9d1d9] px-2 py-1 rounded border border-[#30363d] transition-colors"
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            {submitError && (
              <p className="text-xs text-red-400 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" /> {submitError}
              </p>
            )}

            <div className="pt-2">
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
        <div className="flex gap-1.5 border-b border-[#30363d] pb-2 text-xs">
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

                <div>
                  <Link
                    to={`/tasks/${task.id}`}
                    className="btn btn-secondary text-xs flex items-center gap-1.5 py-1.5 px-3 whitespace-nowrap"
                  >
                    Open Workspace <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
