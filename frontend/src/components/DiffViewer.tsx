import { useState } from 'react'
import { Check, Copy, FileCode, GitCompare, Plus, Minus } from 'lucide-react'

interface DiffViewerProps {
  diff: string
  filesChanged?: string[]
  linesAdded?: number
  linesRemoved?: number
}

interface ParsedFileDiff {
  filename: string
  lines: Array<{
    type: 'add' | 'del' | 'header' | 'context'
    content: string
    oldLineNo?: number
    newLineNo?: number
  }>
}

function parseUnifiedDiff(rawDiff: string): ParsedFileDiff[] {
  if (!rawDiff.trim()) return []

  const fileDiffs: ParsedFileDiff[] = []
  const rawFiles = rawDiff.split(/(?=diff --git|--- \/dev\/null|--- a\/)/)

  for (const rawFile of rawFiles) {
    if (!rawFile.trim()) continue

    const lines = rawFile.split(/\r?\n/)
    let filename = 'unknown'

    for (const l of lines) {
      if (l.startsWith('+++ b/')) {
        filename = l.slice(6).trim()
        break
      } else if (l.startsWith('diff --git a/')) {
        const parts = l.split(' ')
        if (parts.length >= 4) {
          filename = parts[3].replace(/^b\//, '')
        }
      }
    }

    const parsedLines: ParsedFileDiff['lines'] = []
    let oldLine = 0
    let newLine = 0

    for (const line of lines) {
      if (line.startsWith('@@')) {
        const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/)
        if (match) {
          oldLine = parseInt(match[1], 10)
          newLine = parseInt(match[2], 10)
        }
        parsedLines.push({ type: 'header', content: line })
      } else if (line.startsWith('+') && !line.startsWith('+++')) {
        parsedLines.push({ type: 'add', content: line, newLineNo: newLine++ })
      } else if (line.startsWith('-') && !line.startsWith('---')) {
        parsedLines.push({ type: 'del', content: line, oldLineNo: oldLine++ })
      } else if (!line.startsWith('diff') && !line.startsWith('index') && !line.startsWith('---') && !line.startsWith('+++')) {
        parsedLines.push({ type: 'context', content: line, oldLineNo: oldLine++, newLineNo: newLine++ })
      }
    }

    fileDiffs.push({ filename, lines: parsedLines })
  }

  return fileDiffs
}

export function DiffViewer({ diff, filesChanged = [], linesAdded = 0, linesRemoved = 0 }: DiffViewerProps) {
  const [copied, setCopied] = useState(false)
  const fileDiffs = parseUnifiedDiff(diff)
  const [selectedFileIdx, setSelectedFileIdx] = useState(0)

  const handleCopy = () => {
    navigator.clipboard.writeText(diff)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!diff || fileDiffs.length === 0) {
    return (
      <div className="surface p-8 text-center text-[#8b949e]">
        <GitCompare className="w-8 h-8 mx-auto mb-2 opacity-40" />
        <p className="text-sm text-white font-medium">No Code Changes Generated Yet</p>
        <p className="text-xs mt-1">Changes applied during the implementation node will appear here as a Git diff.</p>
      </div>
    )
  }

  const currentDiff = fileDiffs[selectedFileIdx] || fileDiffs[0]

  return (
    <div className="surface overflow-hidden border border-[#30363d] rounded-md text-xs">
      {/* Diff Header */}
      <div className="bg-[#161b22] px-4 py-3 border-b border-[#30363d] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 font-semibold text-white">
            <GitCompare className="w-4 h-4 text-green-400" />
            <span>Git Diff</span>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="flex items-center text-green-400 font-mono">
              <Plus className="w-3 h-3" /> {linesAdded}
            </span>
            <span className="flex items-center text-red-400 font-mono">
              <Minus className="w-3 h-3" /> {linesRemoved}
            </span>
            <span className="text-[#8b949e]">
              ({filesChanged.length || fileDiffs.length} files modified)
            </span>
          </div>
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-[#8b949e] hover:text-white px-2.5 py-1 rounded bg-[#21262d] border border-[#30363d] transition-colors self-start sm:self-auto"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? 'Copied Diff' : 'Copy Raw Diff'}
        </button>
      </div>

      {/* File Navigation Tabs */}
      {fileDiffs.length > 1 && (
        <div className="bg-[#0d1117] px-2 py-1.5 border-b border-[#30363d] flex gap-1 overflow-x-auto">
          {fileDiffs.map((fd, i) => (
            <button
              key={i}
              onClick={() => setSelectedFileIdx(i)}
              className={`px-2.5 py-1 rounded text-xs font-mono flex items-center gap-1.5 transition-colors whitespace-nowrap ${
                selectedFileIdx === i
                  ? 'bg-[#21262d] text-white border border-[#30363d]'
                  : 'text-[#8b949e] hover:text-white'
              }`}
            >
              <FileCode className="w-3 h-3 text-blue-400" />
              {fd.filename}
            </button>
          ))}
        </div>
      )}

      {/* Current File Banner */}
      <div className="bg-[#0d1117] px-4 py-2 border-b border-[#30363d] font-mono text-xs text-[#e6edf3] font-semibold flex items-center gap-2">
        <FileCode className="w-3.5 h-3.5 text-blue-400" />
        {currentDiff.filename}
      </div>

      {/* Diff Code Area */}
      <div className="bg-[#0d1117] overflow-x-auto font-mono text-xs leading-relaxed max-h-[500px] overflow-y-auto">
        <table className="w-full border-collapse">
          <tbody>
            {currentDiff.lines.map((line, idx) => {
              if (line.type === 'header') {
                return (
                  <tr key={idx} className="bg-blue-950/30 text-blue-300 font-bold border-y border-blue-900/40 select-none">
                    <td className="py-1 px-3 text-[#6e7681] text-right w-10 text-[10px]">...</td>
                    <td className="py-1 px-3 text-[#6e7681] text-right w-10 text-[10px]">...</td>
                    <td className="py-1 px-3">{line.content}</td>
                  </tr>
                )
              }

              const isAdd = line.type === 'add'
              const isDel = line.type === 'del'

              return (
                <tr
                  key={idx}
                  className={`${
                    isAdd
                      ? 'bg-green-950/40 text-green-300'
                      : isDel
                      ? 'bg-red-950/40 text-red-300'
                      : 'text-[#e6edf3] hover:bg-[#161b22]'
                  }`}
                >
                  <td className="py-0.5 px-2 text-[#6e7681] text-right w-10 select-none border-r border-[#30363d]/50 text-[10px]">
                    {line.oldLineNo ?? ''}
                  </td>
                  <td className="py-0.5 px-2 text-[#6e7681] text-right w-10 select-none border-r border-[#30363d]/50 text-[10px]">
                    {line.newLineNo ?? ''}
                  </td>
                  <td className="py-0.5 px-3 whitespace-pre">{line.content}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
