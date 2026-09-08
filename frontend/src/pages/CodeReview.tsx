import { useParams } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'

/** Phase 9: Full code review findings with severity breakdown */
export function CodeReview() {
  const { taskId } = useParams<{ taskId: string }>()

  return (
    <div className="max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <ShieldCheck className="w-6 h-6" /> Code Review
        </h1>
        <p className="text-[#8b949e] mt-1">Task: {taskId}</p>
      </div>
      <div className="surface p-8 text-center">
        <ShieldCheck className="w-8 h-8 text-[#8b949e] mx-auto mb-2" />
        <p className="text-[#8b949e] text-sm">
          AI code review findings will appear here after the review agent runs.
        </p>
        <p className="text-[#8b949e] text-xs mt-1">Implemented in Phase 8 / 9.</p>
      </div>
    </div>
  )
}
