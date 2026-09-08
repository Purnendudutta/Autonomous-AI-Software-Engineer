import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  GitBranch,
  CheckCircle2,
  AlertCircle,
  ListTodo,
  Plus,
  ArrowRight,
  TrendingUp,
  Cpu,
  Clock,
  RotateCcw,
} from 'lucide-react'
import { healthApi, repositoryApi, taskApi } from '@/services/api'
import type { HealthResponse, Repository, Task } from '@/types'

const STATUS_COLORS: Record<string, string> = {
  pending:        'badge-neutral',
  running:        'badge-info',
  succeeded:      'badge-success',
  partial_success:'badge-warning',
  failed:         'badge-danger',
  blocked:        'badge-danger',
  cancelled:      'badge-neutral',
}

function StatCard({
  label,
  value,
  icon: Icon,
  color,
  subtext,
}: {
  label: string
  value: string | number
  icon: React.ElementType
  color: string
  subtext?: string
}) {
  return (
    <div className="surface p-4 flex items-start justify-between">
      <div className="space-y-1">
        <p className="text-xs text-[#8b949e] uppercase font-semibold tracking-wider">{label}</p>
        <p className="text-2xl font-bold text-white tracking-tight">{value}</p>
        {subtext && <p className="text-[11px] text-[#6e7681]">{subtext}</p>}
      </div>
      <div className={`p-2.5 rounded-lg ${color}`}>
        <Icon className="w-5 h-5" />
      </div>
    </div>
  )
}

export function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [repos, setRepos] = useState<Repository[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      healthApi.check().catch(() => null),
      repositoryApi.list().catch(() => []),
      taskApi.list().catch(() => []),
    ]).then(([h, r, t]) => {
      setHealth(h)
      setRepos(r)
      setTasks(t)
      setLoading(false)
    })
  }, [])

  const activeTasks = tasks.filter((t) => t.status === 'running' || t.status === 'pending').length
  const completedTasks = tasks.filter((t) => t.status === 'succeeded').length
  const successRate = tasks.length > 0 ? Math.round((completedTasks / tasks.length) * 100) : 100

  return (
    <div className="max-w-6xl space-y-6">
      {/* Header & Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">System Overview</h1>
          <p className="text-[#8b949e] text-xs mt-0.5">
            Autonomous AI Software Engineer · Multi-Agent Orchestration Engine
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/repositories"
            className="btn btn-secondary text-xs flex items-center gap-1.5 py-1.5 px-3"
          >
            <Plus className="w-3.5 h-3.5" /> Add Repository
          </Link>
          <Link
            to="/tasks"
            className="btn btn-primary text-xs flex items-center gap-1.5 py-1.5 px-3"
          >
            <Plus className="w-3.5 h-3.5" /> Submit Task
          </Link>
        </div>
      </div>

      {/* Engine Status Banner */}
      <div
        className={`p-4 rounded-lg border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
          health?.status === 'ok'
            ? 'bg-green-950/20 border-green-800'
            : loading
            ? 'bg-gray-900 border-gray-800'
            : 'bg-red-950/20 border-red-800'
        }`}
      >
        <div className="flex items-center gap-3">
          {health?.status === 'ok' ? (
            <div className="w-8 h-8 rounded-full bg-green-900/40 border border-green-700 flex items-center justify-center flex-shrink-0">
              <CheckCircle2 className="w-4 h-4 text-green-400" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-full bg-red-900/40 border border-red-700 flex items-center justify-center flex-shrink-0">
              <AlertCircle className="w-4 h-4 text-red-400" />
            </div>
          )}
          <div>
            <p className="font-semibold text-white text-xs">
              {loading
                ? 'Connecting to AI Engine services…'
                : health?.status === 'ok'
                ? 'All Autonomous Agent Systems Online'
                : 'AI Service Warning'}
            </p>
            {health && (
              <p className="text-[11px] text-[#8b949e] font-mono mt-0.5">
                Backend v{health.version} · DB: {health.db} · LLM Model: {health.llm_model}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 text-[11px] text-[#8b949e] font-mono">
          <span className="flex items-center gap-1 bg-[#0d1117] px-2 py-1 rounded border border-[#30363d]">
            <Cpu className="w-3 h-3 text-blue-400" /> 12 Agent Nodes Active
          </span>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Ingested Repositories"
          value={repos.length}
          icon={GitBranch}
          color="bg-blue-950/60 text-blue-400 border border-blue-800"
          subtext={`${repos.length} indexed with pgvector`}
        />
        <StatCard
          label="Active Tasks"
          value={activeTasks}
          icon={Activity}
          color="bg-purple-950/60 text-purple-400 border border-purple-800"
          subtext="In execution pipeline"
        />
        <StatCard
          label="Completed Tasks"
          value={completedTasks}
          icon={CheckCircle2}
          color="bg-green-950/60 text-green-400 border border-green-800"
          subtext="Verified & PR generated"
        />
        <StatCard
          label="Resolution Success Rate"
          value={`${successRate}%`}
          icon={TrendingUp}
          color="bg-yellow-950/60 text-yellow-400 border border-yellow-800"
          subtext="Autonomous pass rate"
        />
      </div>

      {/* Two Column Layout: Recent Tasks & Repositories */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Tasks (2 cols) */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <ListTodo className="w-4 h-4 text-blue-400" />
              Recent Autonomous Engineering Tasks
            </h2>
            <Link to="/tasks" className="text-xs text-blue-400 hover:underline flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {tasks.length === 0 ? (
            <div className="surface p-8 text-center text-[#8b949e]">
              <ListTodo className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-xs text-white font-medium">No Engineering Tasks Yet</p>
              <p className="text-[11px] mt-1">Submit your first task to see the agent in action.</p>
              <Link to="/tasks" className="btn btn-primary text-xs mt-3 inline-flex items-center gap-1.5">
                <Plus className="w-3.5 h-3.5" /> Create Task
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {tasks.slice(0, 5).map((t) => (
                <Link
                  key={t.id}
                  to={`/tasks/${t.id}`}
                  className="surface p-3.5 flex items-center justify-between hover:border-[#58a6ff] transition-colors group block"
                >
                  <div className="space-y-1 min-w-0 pr-3">
                    <p className="text-xs font-medium text-white group-hover:text-blue-400 transition-colors truncate">
                      {t.description}
                    </p>
                    <div className="flex items-center gap-3 text-[10px] text-[#8b949e]">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" /> {new Date(t.created_at).toLocaleTimeString()}
                      </span>
                      {t.retry_count > 0 && (
                        <span className="flex items-center gap-1 text-yellow-400 font-medium">
                          <RotateCcw className="w-3 h-3" /> {t.retry_count} retries
                        </span>
                      )}
                    </div>
                  </div>

                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold flex-shrink-0 ${STATUS_COLORS[t.status] || 'badge-neutral'}`}>
                    {t.status}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Repositories Sidebar (1 col) */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-purple-400" />
              Repositories ({repos.length})
            </h2>
            <Link to="/repositories" className="text-xs text-blue-400 hover:underline flex items-center gap-1">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {repos.length === 0 ? (
            <div className="surface p-6 text-center text-[#8b949e]">
              <GitBranch className="w-6 h-6 mx-auto mb-2 opacity-40" />
              <p className="text-xs text-white font-medium">No Repositories</p>
              <Link to="/repositories" className="btn btn-secondary text-xs mt-2 inline-flex items-center gap-1">
                Add Repo
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {repos.slice(0, 4).map((repo) => (
                <Link
                  key={repo.id}
                  to={`/repositories/${repo.id}`}
                  className="surface p-3 block hover:border-[#58a6ff] transition-colors group"
                >
                  <p className="text-xs font-semibold text-white group-hover:text-blue-400 truncate">
                    {repo.owner}/{repo.name}
                  </p>
                  <p className="text-[10px] text-[#8b949e] font-mono mt-0.5 truncate">
                    {repo.url}
                  </p>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
