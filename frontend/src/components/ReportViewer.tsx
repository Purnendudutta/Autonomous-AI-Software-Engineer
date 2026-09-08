import { useState } from 'react'
import { Check, Copy, FileText, ShieldCheck, GitPullRequest } from 'lucide-react'
import type { ReportResponse } from '@/types'

interface ReportViewerProps {
  report: ReportResponse | null
}

export function ReportViewer({ report }: ReportViewerProps) {
  const [copied, setCopied] = useState(false)

  if (!report) {
    return (
      <div className="surface p-8 text-center text-[#8b949e]">
        <FileText className="w-8 h-8 mx-auto mb-2 opacity-40" />
        <p className="text-sm text-white font-medium">Pull Request Report Pending</p>
        <p className="text-xs mt-1">The PR report will be automatically compiled once the agent workflow completes verification.</p>
      </div>
    )
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(report.full_report_markdown || '')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-4 text-xs">
      {/* Header card with Copy button */}
      <div className="surface p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <GitPullRequest className="w-4 h-4 text-purple-400" />
            <h2 className="text-sm font-bold text-white">{report.title}</h2>
          </div>
          <p className="text-[#8b949e] text-xs">{report.summary}</p>
        </div>

        <div className="flex items-center gap-2">
          <span className="bg-green-950/40 text-green-300 border border-green-800 text-[11px] font-bold px-2.5 py-1 rounded-full flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-green-400" />
            {report.verification_status}
          </span>
          <button
            onClick={handleCopy}
            className="btn btn-secondary text-xs flex items-center gap-1.5 py-1 px-3"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied' : 'Copy Report'}
          </button>
        </div>
      </div>

      {/* Structured Details Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="surface p-3 space-y-1">
          <p className="text-[10px] uppercase font-bold text-[#8b949e]">Problem Statement</p>
          <p className="text-xs text-[#e6edf3] leading-relaxed">{report.problem_description}</p>
        </div>
        <div className="surface p-3 space-y-1">
          <p className="text-[10px] uppercase font-bold text-blue-400">Root Cause Analysis</p>
          <p className="text-xs text-[#e6edf3] leading-relaxed">{report.root_cause}</p>
        </div>
      </div>

      {/* Full Markdown Report Document */}
      <div className="surface p-5 space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-white border-b border-[#30363d] pb-2">
          Pull Request Markdown Document
        </h3>
        <pre className="bg-[#0d1117] p-4 rounded font-mono text-xs text-[#e6edf3] overflow-x-auto border border-[#30363d] leading-relaxed whitespace-pre-wrap max-h-[600px] overflow-y-auto">
          {report.full_report_markdown}
        </pre>
      </div>
    </div>
  )
}
