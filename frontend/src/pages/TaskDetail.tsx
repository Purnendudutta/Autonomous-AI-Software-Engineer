import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Activity, Clock, GitCompare, RotateCcw, ShieldCheck, Target, Terminal, Shield, GitPullRequest } from 'lucide-react'
import { useTask } from '@/hooks/useTask'
import { useSSE } from '@/hooks/useSSE'
import { taskApi } from '@/services/api'
import { PlanViewer } from '@/components/PlanViewer'
import { DiffViewer } from '@/components/DiffViewer'
import { TestResultsViewer } from '@/components/TestResultsViewer'
import { CodeReviewViewer } from '@/components/CodeReviewViewer'
import { ReportViewer } from '@/components/ReportViewer'
import type { CodeReviewResponse, DiffResponse, ReportResponse, TestRun } from '@/types'

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
  const { task, loading, error } = useTask(taskId ?? null)
  const [activeTab, setActiveTab] = useState<'plan' | 'diff' | 'tests' | 'review' | 'report'>('plan')
  const [diffData, setDiffData] = useState<DiffResponse | null>(null)
  const [testRuns, setTestRuns] = useState<TestRun[]>([])
  const [reviewData, setReviewData] = useState<CodeReviewResponse | null>(null)
  const [reportData, setReportData] = useState<ReportResponse | null>(null)

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
      </div>

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
