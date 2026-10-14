import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  Activity,
  Clock,
  GitCompare,
  RotateCcw,
  ShieldCheck,
  Target,
  Terminal,
  Shield,
  GitPullRequest,
  UploadCloud,
  ExternalLink,
  Loader2,
  CheckCircle2,
} from 'lucide-react'
import { useTask } from '@/hooks/useTask'
import { useSSE } from '@/hooks/useSSE'
import { taskApi } from '@/services/api'
import { PlanViewer } from '@/components/PlanViewer'
import { DiffViewer } from '@/components/DiffViewer'
import { TestResultsViewer } from '@/components/TestResultsViewer'
import { CodeReviewViewer } from '@/components/CodeReviewViewer'
import { ReportViewer } from '@/components/ReportViewer'
import type { CodeReviewResponse, DiffResponse, ReportResponse, TaskGitPushResponse, TestRun } from '@/types'

const STATUS_COLORS: Record<string, string> = {
  pending:        'badge-neutral',
  running:        'badge-info',
  succeeded:      'badge-success',
  partial_success:'badge-warning',
  failed:         'badge-danger',
  blocked:        'badge-danger',
  cancelled:      'badge-neutral',
}

const GRAPH_NODES = [
  { key: 'task_understanding', label: 'Understand' },
  { key: 'code_retrieval', label: 'RAG Retrieval' },
  { key: 'planning', label: 'Plan Strategy' },
  { key: 'implementation', label: 'Code Edit' },
  { key: 'test_execution', label: 'Sandbox Tests' },
  { key: 'failure_analysis', label: 'Self-Correction' },
  { key: 'verification', label: 'Verify' },
  { key: 'final_report', label: 'PR Report' },
] as const

export function TaskDetail() {
  const { taskId } = useParams<{ taskId: string }>()
  const { task, loading, error, refetch } = useTask(taskId ?? null)
  const [activeTab, setActiveTab] = useState<'plan' | 'diff' | 'tests' | 'review' | 'report'>('plan')
  const [diffData, setDiffData] = useState<DiffResponse | null>(null)
  const [testRuns, setTestRuns] = useState<TestRun[]>([])
  const [reviewData, setReviewData] = useState<CodeReviewResponse | null>(null)
  const [reportData, setReportData] = useState<ReportResponse | null>(null)
  const [retrying, setRetrying] = useState(false)

  // GitHub Commit & Push state
  const [showPushPanel, setShowPushPanel] = useState(false)
  const [commitMessage, setCommitMessage] = useState('')
  const [pushBranch, setPushBranch] = useState('')
  const [githubToken, setGithubToken] = useState('')
  const [pushing, setPushing] = useState(false)
  const [pushResult, setPushResult] = useState<TaskGitPushResponse | null>(null)
  const [pushError, setPushError] = useState<string | null>(null)

  const { events, connected } = useSSE(
    task && !['succeeded', 'failed', 'cancelled', 'blocked'].includes(task.status)
      ? taskApi.getLogsUrl(taskId!)
      : null
  )

  useEffect(() => {
    if (taskId) {
      taskApi.getDiff(taskId).then(setDiffData).catch(() => setDiffData(null))
      taskApi.getTests(taskId).then(setTestRuns).catch(() => setTestRuns([]))
      taskApi.getReview(taskId).then(setReviewData).catch(() => setReviewData(null))
      taskApi.getReport(taskId).then(setReportData).catch(() => setReportData(null))
    }
  }, [taskId, task?.status])

  useEffect(() => {
    if (task && !commitMessage) {
      setCommitMessage(`feat(ai): ${task.description.slice(0, 72)}`)
    }
    if (task?.branch && !pushBranch) {
      setPushBranch(task.branch)
    }
  }, [task, commitMessage, pushBranch])

  const handleRetry = async () => {
    if (!taskId) return
    setRetrying(true)
    try {
      await taskApi.retry(taskId)
      refetch()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to retry task')
    } finally {
      setRetrying(false)
    }
  }

  const handlePushToGithub = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!taskId) return
    setPushing(true)
    setPushError(null)
    try {
      const res = await taskApi.pushToGithub(taskId, {
        commit_message: commitMessage.trim() || undefined,
        branch: pushBranch.trim() || undefined,
        github_token: githubToken.trim() || undefined,
      })
      setPushResult(res)
    } catch (err) {
      setPushError(err instanceof Error ? err.message : 'Failed to push commit to GitHub')
    } finally {
      setPushing(false)
    }
  }

  if (loading) return <p className="text-[#8b949e]">Loading task…</p>
  if (error)   return <p className="text-red-400">{error}</p>
  if (!task)   return <p className="text-[#8b949e]">Task not found.</p>

  // Determine current active or completed nodes from events
  const visitedNodes = new Set(events.map((e) => e.node_name))
  const lastEvent = events[events.length - 1]
  const currentNode = lastEvent?.node_name

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-xl font-bold text-white">Task Details</h1>
            <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${STATUS_COLORS[task.status] || 'badge-neutral'}`}>
              {task.status}
            </span>
            {task.status === 'succeeded' && (
              <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-green-950/50 text-green-300 border border-green-800 flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-green-400" />
                VERIFIED: SUCCESS
              </span>
            )}
          </div>
          <p className="text-[#8b949e] text-sm">{task.description}</p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <button
            onClick={() => setShowPushPanel((v) => !v)}
            disabled={task.status === 'running'}
            className="px-3 py-1.5 bg-[#238636] hover:bg-[#2ea043] disabled:opacity-50 text-white text-xs font-medium rounded-md flex items-center gap-1.5 transition-colors"
          >
            <UploadCloud className="w-3.5 h-3.5" />
            Commit & Push to GitHub
          </button>

          <button
            onClick={handleRetry}
            disabled={retrying || task.status === 'running'}
            className="btn btn-secondary text-xs flex items-center gap-1.5 py-1.5 px-3"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${retrying ? 'animate-spin' : ''}`} />
            {retrying ? 'Re-launching…' : 'Re-run Task'}
          </button>
        </div>
      </div>

      {/* Commit & Push to GitHub Panel */}
      {showPushPanel && (
        <div className="surface p-4 border border-[#238636]/60 bg-[#0d1117] space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-green-400 flex items-center gap-1.5">
              <UploadCloud className="w-4 h-4" />
              Commit & Push Changes to Original GitHub Repository
            </h3>
            <button
              type="button"
              onClick={() => setShowPushPanel(false)}
              className="text-xs text-[#8b949e] hover:text-white"
            >
              Close
            </button>
          </div>

          {pushResult ? (
            <div className="p-3 rounded-md bg-green-950/40 border border-green-800 text-xs text-green-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0" />
                <span>
                  {pushResult.message} — Branch: <strong className="font-mono">{pushResult.branch}</strong>
                </span>
              </div>
              <a
                href={pushResult.commit_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-green-300 hover:text-white underline font-mono"
              >
                View Commit on GitHub ({pushResult.commit_sha.slice(0, 7)})
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          ) : (
            <form onSubmit={handlePushToGithub} className="grid grid-cols-1 md:grid-cols-12 gap-3">
              <div className="md:col-span-5">
                <label className="block text-[11px] text-[#8b949e] mb-1">Commit Message</label>
                <input
                  type="text"
                  value={commitMessage}
                  onChange={(e) => setCommitMessage(e.target.value)}
                  placeholder="feat(ai): implement requested changes"
                  className="w-full px-3 py-1.5 bg-[#161b22] border border-[#30363d] rounded text-xs text-white focus:outline-none focus:border-[#388bfd]"
                  required
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-[11px] text-[#8b949e] mb-1">Target Branch</label>
                <input
                  type="text"
                  value={pushBranch}
                  onChange={(e) => setPushBranch(e.target.value)}
                  placeholder="main"
                  className="w-full px-3 py-1.5 bg-[#161b22] border border-[#30363d] rounded text-xs text-white font-mono focus:outline-none focus:border-[#388bfd]"
                />
              </div>
              <div className="md:col-span-3">
                <label className="block text-[11px] text-[#8b949e] mb-1">
                  GitHub Token (optional if in <code className="text-[#e6edf3]">.env</code>)
                </label>
                <input
                  type="password"
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  placeholder="ghp_... or github_pat_..."
                  className="w-full px-3 py-1.5 bg-[#161b22] border border-[#30363d] rounded text-xs text-white font-mono focus:outline-none focus:border-[#388bfd]"
                />
              </div>
              <div className="md:col-span-2 flex items-end">
                <button
                  type="submit"
                  disabled={pushing}
                  className="w-full py-1.5 px-3 bg-[#238636] hover:bg-[#2ea043] disabled:opacity-50 text-white text-xs font-medium rounded flex items-center justify-center gap-1.5 transition-colors"
                >
                  {pushing ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Pushing…
                    </>
                  ) : (
                    <>
                      <UploadCloud className="w-3.5 h-3.5" />
                      Push Now
                    </>
                  )}
                </button>
              </div>
            </form>
          )}

          {pushError && (
            <p className="text-xs text-red-400 font-mono bg-red-950/30 border border-red-800/60 p-2 rounded">
              {pushError}
            </p>
          )}
        </div>
      )}

      {/* Error Diagnostic Banner if Task Failed */}
      {task.error_message && (
        <div className="p-4 rounded-lg bg-red-950/30 border border-red-800/80 text-xs text-red-200 space-y-1">
          <p className="font-semibold text-red-300">Task Diagnostic Details:</p>
          <p className="font-mono break-all text-[11px]">{task.error_message}</p>
        </div>
      )}

      {/* Workflow Step Indicator */}
      <div className="surface p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-[#8b949e] mb-3">
          LangGraph Autonomous Pipeline & Verification
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-8 gap-2">
          {GRAPH_NODES.map((node, i) => {
            const isCurrent = currentNode === node.key && task.status === 'running'
            const isDone = visitedNodes.has(node.key) || task.status === 'succeeded'

            return (
              <div
                key={node.key}
                className={`p-2 rounded border text-center transition-all ${
                  isCurrent
                    ? 'bg-blue-900/30 border-blue-500 text-blue-300 font-bold shadow-sm ring-1 ring-blue-500/50'
                    : isDone
                    ? 'bg-green-900/20 border-green-800 text-green-300'
                    : 'bg-[#0d1117] border-[#30363d] text-[#6e7681]'
                }`}
              >
                <span className="text-[9px] block opacity-60">0{i + 1}</span>
                <span className="text-xs truncate block">{node.label}</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Metadata Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="surface p-3">
          <p className="text-xs text-[#8b949e]">Task ID</p>
          <p className="text-xs font-mono text-white mt-1 truncate">{task.id}</p>
        </div>
        <div className="surface p-3">
          <p className="text-xs text-[#8b949e] flex items-center gap-1">
            <RotateCcw className="w-3.5 h-3.5" /> Self-Correction Retries
          </p>
          <p className="text-sm font-bold text-white mt-1">
            {task.retry_count} / 3 {task.retry_count > 0 && <span className="text-xs font-normal text-yellow-400 font-sans">(Self-corrected {task.retry_count}x)</span>}
          </p>
        </div>
        <div className="surface p-3">
          <p className="text-xs text-[#8b949e] flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" /> Created Timestamp
          </p>
          <p className="text-xs text-white mt-1">
            {new Date(task.created_at).toLocaleString()}
          </p>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="flex items-center gap-2 border-b border-[#30363d] pb-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab('plan')}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
            activeTab === 'plan'
              ? 'bg-[#21262d] text-white border border-[#30363d]'
              : 'text-[#8b949e] hover:text-white'
          }`}
        >
          <Target className="w-4 h-4 text-blue-400" />
          Plan & Activity
        </button>

        <button
          onClick={() => setActiveTab('diff')}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
            activeTab === 'diff'
              ? 'bg-[#21262d] text-white border border-[#30363d]'
              : 'text-[#8b949e] hover:text-white'
          }`}
        >
          <GitCompare className="w-4 h-4 text-green-400" />
          Git Diff
          {diffData && diffData.files_changed.length > 0 && (
            <span className="text-[10px] bg-[#238636] text-white px-1.5 py-0.2 rounded-full ml-1">
              {diffData.files_changed.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('tests')}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
            activeTab === 'tests'
              ? 'bg-[#21262d] text-white border border-[#30363d]'
              : 'text-[#8b949e] hover:text-white'
          }`}
        >
          <Terminal className="w-4 h-4 text-purple-400" />
          Sandbox Tests
          {testRuns.length > 0 && (
            <span className="text-[10px] bg-[#8957e5] text-white px-1.5 py-0.2 rounded-full ml-1">
              {testRuns.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('review')}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
            activeTab === 'review'
              ? 'bg-[#21262d] text-white border border-[#30363d]'
              : 'text-[#8b949e] hover:text-white'
          }`}
        >
          <Shield className="w-4 h-4 text-yellow-400" />
          AI Code Review
          {reviewData && reviewData.findings.length > 0 && (
            <span className="text-[10px] bg-[#d29922] text-black font-bold px-1.5 py-0.2 rounded-full ml-1">
              {reviewData.findings.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('report')}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
            activeTab === 'report'
              ? 'bg-[#21262d] text-white border border-[#30363d]'
              : 'text-[#8b949e] hover:text-white'
          }`}
        >
          <GitPullRequest className="w-4 h-4 text-pink-400" />
          PR Report
        </button>
      </div>

      {activeTab === 'diff' ? (
        <DiffViewer
          diff={diffData?.diff || ''}
          filesChanged={diffData?.files_changed}
          linesAdded={diffData?.lines_added}
          linesRemoved={diffData?.lines_removed}
        />
      ) : activeTab === 'tests' ? (
        <TestResultsViewer testRuns={testRuns} />
      ) : activeTab === 'review' ? (
        <CodeReviewViewer review={reviewData} />
      ) : activeTab === 'report' ? (
        <ReportViewer report={reportData} />
      ) : (
        <div className="space-y-6">
          {/* Structured Execution Plan */}
          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <Target className="w-4 h-4 text-blue-400" />
              Execution Plan & Strategy
            </h2>
            <PlanViewer plan={task.execution_plan} />
          </div>

          {/* Agent Live Activity Logs */}
          <div>
            <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Activity className="w-4 h-4 text-green-400" />
              Live Agent Execution Stream
              {connected && (
                <span className="flex items-center gap-1 text-[11px] text-green-400 font-normal">
                  <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                  Live SSE Connected
                </span>
              )}
            </h2>
            <div className="surface p-4 font-mono text-xs text-[#8b949e] min-h-[180px] max-h-[380px] overflow-y-auto space-y-1.5">
              {events.length === 0 ? (
                <p className="text-center py-8 text-[#8b949e]">
                  {task.status === 'pending'
                    ? 'Task is queued. Agent will start shortly…'
                    : 'No agent events streamed yet.'}
                </p>
              ) : (
                events.map((e, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-[#6e7681] flex-shrink-0">
                      [{new Date(e.timestamp).toLocaleTimeString()}]
                    </span>
                    <span
                      className={`font-semibold flex-shrink-0 ${
                        e.status === 'failed'
                          ? 'text-red-400'
                          : e.status === 'succeeded'
                          ? 'text-green-400'
                          : 'text-blue-400'
                      }`}
                    >
                      [{e.node_name}]
                    </span>
                    <span className="text-[#e6edf3]">{e.message}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
