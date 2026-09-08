import { CheckCircle2, FileCode2, Lightbulb, ListChecks, ShieldCheck, Target } from 'lucide-react'
import type { ExecutionPlan } from '@/types'

interface PlanViewerProps {
  plan?: ExecutionPlan | null
}

const ACTION_BADGES: Record<string, string> = {
  modify_code: 'bg-blue-900/40 text-blue-300 border-blue-800',
  create_file: 'bg-green-900/40 text-green-300 border-green-800',
  read_file: 'bg-gray-800 text-gray-300 border-gray-700',
  run_tests: 'bg-purple-900/40 text-purple-300 border-purple-800',
  verify: 'bg-emerald-900/40 text-emerald-300 border-emerald-800',
}

export function PlanViewer({ plan }: PlanViewerProps) {
  if (!plan) {
    return (
      <div className="surface p-8 text-center text-[#8b949e]">
        <Target className="w-8 h-8 mx-auto mb-2 opacity-40" />
        <p className="text-sm text-white font-medium">Execution Plan Pending</p>
        <p className="text-xs mt-1">The planning node is analyzing the codebase context to formulate a step-by-step strategy.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4 text-xs">
      {/* Overview & Root Cause Analysis */}
      <div className="surface p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-[#30363d] pb-2">
          <h3 className="font-semibold text-white uppercase tracking-wider text-[11px] flex items-center gap-1.5">
            <Lightbulb className="w-4 h-4 text-yellow-400" />
            Root Cause & Strategy Analysis
          </h3>
          <span className="text-[10px] uppercase font-bold bg-[#21262d] text-blue-400 px-2 py-0.5 rounded border border-[#30363d]">
            {plan.task_type}
          </span>
        </div>

        {plan.root_cause_analysis && (
          <p className="text-[#e6edf3] leading-relaxed">
            {plan.root_cause_analysis}
          </p>
        )}

        {/* Target Files */}
        {plan.target_files && plan.target_files.length > 0 && (
          <div>
            <span className="text-[#8b949e] font-medium block mb-1">Target Files:</span>
            <div className="flex flex-wrap gap-1.5">
              {plan.target_files.map((file, i) => (
                <span
                  key={i}
                  className="font-mono text-[11px] bg-[#0d1117] text-[#e6edf3] border border-[#30363d] px-2 py-0.5 rounded flex items-center gap-1"
                >
                  <FileCode2 className="w-3 h-3 text-blue-400" />
                  {file}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Step-by-Step Instructions */}
      <div className="surface p-4 space-y-3">
        <h3 className="font-semibold text-white uppercase tracking-wider text-[11px] flex items-center gap-1.5 border-b border-[#30363d] pb-2">
          <ListChecks className="w-4 h-4 text-blue-400" />
          Planned Action Steps ({plan.steps?.length || 0})
        </h3>

        <div className="space-y-2">
          {plan.steps && plan.steps.map((step) => (
            <div
              key={step.step_number}
              className="bg-[#0d1117] p-3 rounded border border-[#30363d] flex items-start gap-3"
            >
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-[#21262d] text-white flex items-center justify-center font-bold text-[10px]">
                {step.step_number}
              </span>

              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-medium border ${
                      ACTION_BADGES[step.action] || 'bg-gray-800 text-gray-400'
                    }`}
                  >
                    {step.action}
                  </span>
                  <span className="font-mono text-[11px] text-blue-300 font-medium">
                    {step.target_file}
                  </span>
                </div>

                <p className="text-[#e6edf3] leading-relaxed">{step.description}</p>
                {step.rationale && (
                  <p className="text-[#8b949e] text-[11px] italic">
                    Rationale: {step.rationale}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Test & Verification Strategy */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {plan.test_strategy && plan.test_strategy.length > 0 && (
          <div className="surface p-3 space-y-2">
            <h4 className="font-semibold text-white uppercase text-[10px] flex items-center gap-1 text-[#8b949e]">
              <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
              Testing Strategy
            </h4>
            <ul className="space-y-1">
              {plan.test_strategy.map((item, i) => (
                <li key={i} className="text-[#e6edf3] flex items-start gap-1.5 text-[11px]">
                  <span className="text-green-400">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {plan.verification_criteria && plan.verification_criteria.length > 0 && (
          <div className="surface p-3 space-y-2">
            <h4 className="font-semibold text-white uppercase text-[10px] flex items-center gap-1 text-[#8b949e]">
              <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
              Verification Criteria
            </h4>
            <ul className="space-y-1">
              {plan.verification_criteria.map((item, i) => (
                <li key={i} className="text-[#e6edf3] flex items-start gap-1.5 text-[11px]">
                  <span className="text-purple-400">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
