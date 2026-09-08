import { Shield, ShieldAlert, ShieldCheck, Info } from 'lucide-react'
import type { CodeReviewResponse, ReviewFinding } from '@/types'

interface CodeReviewViewerProps {
  review: CodeReviewResponse | null
}

const SEVERITY_BADGES = {
  high: 'bg-red-950/50 text-red-400 border border-red-800',
  medium: 'bg-yellow-950/50 text-yellow-400 border border-yellow-800',
  low: 'bg-blue-950/50 text-blue-400 border border-blue-800',
  info: 'bg-gray-800 text-gray-300 border border-gray-700',
}

export function CodeReviewViewer({ review }: CodeReviewViewerProps) {
  if (!review || (!review.findings.length && review.high_count === 0 && review.medium_count === 0)) {
    return (
      <div className="surface p-8 text-center text-[#8b949e]">
        <ShieldCheck className="w-8 h-8 mx-auto mb-2 text-green-400" />
        <p className="text-sm text-white font-medium">Clean Code Review</p>
        <p className="text-xs mt-1">No security vulnerabilities or code smells detected in the applied modifications.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4 text-xs">
      {/* Metrics Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="surface p-3 flex items-center justify-between">
          <div>
            <p className="text-[#8b949e] text-[11px] font-semibold uppercase">High Severity</p>
            <p className="text-lg font-bold text-red-400 mt-0.5">{review.high_count}</p>
          </div>
          <ShieldAlert className="w-5 h-5 text-red-400 opacity-60" />
        </div>

        <div className="surface p-3 flex items-center justify-between">
          <div>
            <p className="text-[#8b949e] text-[11px] font-semibold uppercase">Medium</p>
            <p className="text-lg font-bold text-yellow-400 mt-0.5">{review.medium_count}</p>
          </div>
          <Shield className="w-5 h-5 text-yellow-400 opacity-60" />
        </div>

        <div className="surface p-3 flex items-center justify-between">
          <div>
            <p className="text-[#8b949e] text-[11px] font-semibold uppercase">Low</p>
            <p className="text-lg font-bold text-blue-400 mt-0.5">{review.low_count}</p>
          </div>
          <Info className="w-5 h-5 text-blue-400 opacity-60" />
        </div>

        <div className="surface p-3 flex items-center justify-between">
          <div>
            <p className="text-[#8b949e] text-[11px] font-semibold uppercase">Info / Notes</p>
            <p className="text-lg font-bold text-gray-300 mt-0.5">{review.info_count}</p>
          </div>
          <ShieldCheck className="w-5 h-5 text-green-400 opacity-60" />
        </div>
      </div>

      {/* Findings List */}
      <div className="surface p-4 space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-white border-b border-[#30363d] pb-2">
          Audit Findings ({review.findings.length})
        </h3>

        <div className="space-y-2.5">
          {review.findings.map((f: ReviewFinding, idx: number) => {
            const sevKey = (f.severity || 'info').toLowerCase() as keyof typeof SEVERITY_BADGES
            return (
              <div
                key={f.id || idx}
                className="bg-[#0d1117] p-3 rounded border border-[#30363d] space-y-2"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                        SEVERITY_BADGES[sevKey] || SEVERITY_BADGES.info
                      }`}
                    >
                      {f.severity}
                    </span>
                    <span className="text-[11px] text-[#8b949e] font-mono uppercase bg-[#21262d] px-1.5 py-0.5 rounded">
                      {f.category}
                    </span>
                    {f.file_path && (
                      <span className="text-xs font-mono text-white font-medium">
                        {f.file_path}
                        {f.line_number ? `:${f.line_number}` : ''}
                      </span>
                    )}
                  </div>
                </div>

                <p className="text-xs text-[#e6edf3] font-medium leading-relaxed">{f.issue}</p>

                {f.recommendation && (
                  <div className="bg-[#161b22] p-2.5 rounded border border-[#30363d]/80 text-[#8b949e]">
                    <span className="text-green-400 font-semibold text-[11px] block mb-0.5">
                      Recommendation:
                    </span>
                    <span className="text-xs text-[#c9d1d9]">{f.recommendation}</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
