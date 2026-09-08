import { useState } from 'react'
import { CheckCircle2, XCircle, Clock, Terminal, AlertTriangle, ChevronDown, ChevronRight, ShieldAlert } from 'lucide-react'
import type { TestRun } from '@/types'

interface TestResultsViewerProps {
  testRuns: TestRun[]
}

export function TestResultsViewer({ testRuns }: TestResultsViewerProps) {
  const [selectedAttemptIdx, setSelectedAttemptIdx] = useState(0)
  const [showLogs, setShowLogs] = useState(false)

  if (!testRuns || testRuns.length === 0) {
    return (
      <div className="surface p-8 text-center text-[#8b949e]">
        <Terminal className="w-8 h-8 mx-auto mb-2 opacity-40" />
        <p className="text-sm text-white font-medium">No Test Runs Executed Yet</p>
        <p className="text-xs mt-1">Tests generated and executed inside the Docker sandbox container will appear here.</p>
      </div>
    )
  }

  const currentRun = testRuns[selectedAttemptIdx] || testRuns[testRuns.length - 1]
  const isPassed = (currentRun.tests_failed || 0) === 0 && currentRun.exit_code === 0 && !currentRun.timed_out

  return (
    <div className="space-y-4 text-xs">
      {/* Header & Attempt Tabs */}
      <div className="surface p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-white uppercase tracking-wider text-[11px]">
            Test Run History:
          </span>
          <div className="flex gap-1.5 overflow-x-auto">
            {testRuns.map((run, idx) => {
              const runPassed = (run.tests_failed || 0) === 0 && run.exit_code === 0
              return (
                <button
                  key={run.id || idx}
                  onClick={() => setSelectedAttemptIdx(idx)}
                  className={`px-2.5 py-1 rounded text-xs font-medium flex items-center gap-1.5 transition-colors ${
                    selectedAttemptIdx === idx
                      ? 'bg-[#21262d] text-white border border-[#30363d]'
                      : 'text-[#8b949e] hover:text-white'
                  }`}
                >
                  {runPassed ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-red-400" />
                  )}
                  Attempt #{run.attempt_number}
                </button>
              )
            })}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`px-2.5 py-1 rounded-full font-bold text-[11px] flex items-center gap-1 ${
              isPassed
                ? 'bg-green-950/40 text-green-400 border border-green-800'
                : 'bg-red-950/40 text-red-400 border border-red-800'
            }`}
          >
            {isPassed ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
            {isPassed ? 'All Tests Passed' : 'Test Failures Detected'}
          </span>
        </div>
      </div>

      {/* Metrics Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="surface p-3">
          <p className="text-[#8b949e] text-[11px]">Total Tests</p>
          <p className="text-lg font-bold text-white mt-0.5">{currentRun.tests_total || 0}</p>
        </div>
        <div className="surface p-3">
          <p className="text-[#8b949e] text-[11px] flex items-center gap-1 text-green-400">
            <CheckCircle2 className="w-3 h-3" /> Passed
          </p>
          <p className="text-lg font-bold text-green-400 mt-0.5">{currentRun.tests_passed || 0}</p>
        </div>
        <div className="surface p-3">
          <p className="text-[#8b949e] text-[11px] flex items-center gap-1 text-red-400">
            <XCircle className="w-3 h-3" /> Failed
          </p>
          <p className="text-lg font-bold text-red-400 mt-0.5">{currentRun.tests_failed || 0}</p>
        </div>
        <div className="surface p-3">
          <p className="text-[#8b949e] text-[11px] flex items-center gap-1">
            <Clock className="w-3 h-3" /> Execution Duration
          </p>
          <p className="text-lg font-bold text-white mt-0.5">
            {currentRun.duration_seconds ? `${currentRun.duration_seconds.toFixed(2)}s` : '< 1s'}
          </p>
        </div>
      </div>

      {/* Executed Command & Timeout notice */}
      <div className="surface p-3 space-y-1">
        <div className="flex items-center justify-between text-[#8b949e]">
          <span className="font-semibold text-white uppercase text-[10px]">Command:</span>
          {currentRun.timed_out && (
            <span className="text-red-400 flex items-center gap-1 font-bold">
              <ShieldAlert className="w-3.5 h-3.5" /> Execution Timed Out
            </span>
          )}
        </div>
        <p className="font-mono text-xs text-[#e6edf3] bg-[#0d1117] p-2 rounded border border-[#30363d]">
          {currentRun.command || 'python -m pytest tests/ -v'}
        </p>
      </div>

      {/* Individual Test Cases List */}
      {currentRun.results && currentRun.results.length > 0 && (
        <div className="surface p-4 space-y-2">
          <h4 className="font-semibold text-white uppercase text-[11px] border-b border-[#30363d] pb-2">
            Executed Test Cases ({currentRun.results.length})
          </h4>
          <div className="space-y-1.5 max-h-[300px] overflow-y-auto">
            {currentRun.results.map((item, i) => (
              <div
                key={i}
                className="bg-[#0d1117] p-2.5 rounded border border-[#30363d] flex items-center justify-between gap-2"
              >
                <div className="flex items-center gap-2 min-w-0">
                  {item.status === 'passed' ? (
                    <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0" />
                  ) : item.status === 'failed' ? (
                    <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                  ) : (
                    <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  )}
                  <div className="truncate">
                    <span className="font-mono font-medium text-white">{item.test_name}</span>
                    {item.test_file && (
                      <span className="text-[#8b949e] font-mono text-[11px] ml-2 truncate">
                        ({item.test_file})
                      </span>
                    )}
                  </div>
                </div>

                <span
                  className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                    item.status === 'passed'
                      ? 'bg-green-950/40 text-green-300'
                      : 'bg-red-950/40 text-red-300'
                  }`}
                >
                  {item.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Collapsible Sandbox Console Logs */}
      <div className="surface p-4 space-y-2">
        <button
          onClick={() => setShowLogs(!showLogs)}
          className="w-full flex items-center justify-between font-semibold text-white uppercase text-[11px]"
        >
          <span className="flex items-center gap-1.5">
            <Terminal className="w-4 h-4 text-blue-400" />
            Sandbox Console Output (stdout / stderr)
          </span>
          {showLogs ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>

        {showLogs && (
          <div className="space-y-2 pt-2">
            {currentRun.stdout && (
              <div>
                <p className="text-[10px] uppercase text-[#8b949e] font-semibold mb-1">STDOUT</p>
                <pre className="bg-[#0d1117] p-3 rounded font-mono text-[11px] text-[#e6edf3] overflow-x-auto max-h-[300px] border border-[#30363d] leading-relaxed whitespace-pre-wrap">
                  {currentRun.stdout}
                </pre>
              </div>
            )}
            {currentRun.stderr && (
              <div>
                <p className="text-[10px] uppercase text-red-400 font-semibold mb-1">STDERR</p>
                <pre className="bg-[#0d1117] p-3 rounded font-mono text-[11px] text-red-300 overflow-x-auto max-h-[300px] border border-red-900/50 leading-relaxed whitespace-pre-wrap">
                  {currentRun.stderr}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
