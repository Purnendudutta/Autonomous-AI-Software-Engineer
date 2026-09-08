import { useParams } from 'react-router-dom'
import { FileCode2 } from 'lucide-react'

/** Phase 9: Full diff viewer with Monaco Editor */
export function CodeChanges() {
  const { taskId } = useParams<{ taskId: string }>()

  return (
    <div className="max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <FileCode2 className="w-6 h-6" /> Code Changes
        </h1>
        <p className="text-[#8b949e] mt-1">Task: {taskId}</p>
      </div>
      <div className="surface p-8 text-center">
        <FileCode2 className="w-8 h-8 text-[#8b949e] mx-auto mb-2" />
        <p className="text-[#8b949e] text-sm">
          Diff viewer will be available once the agent completes code modifications.
        </p>
        <p className="text-[#8b949e] text-xs mt-1">Implemented in Phase 9.</p>
      </div>
    </div>
  )
}
