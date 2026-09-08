import { useState } from 'react'
import { Folder, FolderOpen, FileCode, FileText, ChevronRight, ChevronDown } from 'lucide-react'
import type { FileTreeNode } from '@/types'

interface FileTreeProps {
  node: FileTreeNode
  onSelectFile: (path: string) => void
  selectedPath?: string
  depth?: number
}

export function FileTree({ node, onSelectFile, selectedPath, depth = 0 }: FileTreeProps) {
  const [isOpen, setIsOpen] = useState(depth < 2) // Auto-expand first 2 levels

  if (!node) return null

  if (node.is_dir) {
    return (
      <div className="select-none text-xs">
        <div
          onClick={() => setIsOpen(!isOpen)}
          style={{ paddingLeft: `${depth * 14 + 6}px` }}
          className="flex items-center gap-1.5 py-1 px-2 hover:bg-[#21262d] rounded cursor-pointer text-[#e6edf3] transition-colors"
        >
          {isOpen ? (
            <ChevronDown className="w-3.5 h-3.5 text-[#8b949e] flex-shrink-0" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-[#8b949e] flex-shrink-0" />
          )}
          {isOpen ? (
            <FolderOpen className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
          ) : (
            <Folder className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
          )}
          <span className="font-medium truncate">{node.name}</span>
        </div>

        {isOpen && node.children && (
          <div>
            {node.children.map((child) => (
              <FileTree
                key={child.path || child.name}
                node={child}
                onSelectFile={onSelectFile}
                selectedPath={selectedPath}
                depth={depth + 1}
              />
            ))}
          </div>
        )}
      </div>
    )
  }

  const isSelected = selectedPath === node.path
  const isCode = node.language || ['ts', 'tsx', 'js', 'jsx', 'py', 'json', 'yaml', 'toml', 'sql'].includes(
    node.extension?.replace('.', '') || ''
  )

  return (
    <div
      onClick={() => onSelectFile(node.path)}
      style={{ paddingLeft: `${depth * 14 + 20}px` }}
      className={`flex items-center justify-between py-1 px-2 rounded cursor-pointer text-xs transition-colors ${
        isSelected
          ? 'bg-[#1f6feb]/20 text-blue-300 font-semibold border-l-2 border-[#388bfd]'
          : 'text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d]'
      }`}
    >
      <div className="flex items-center gap-1.5 truncate">
        {isCode ? (
          <FileCode className={`w-3.5 h-3.5 flex-shrink-0 ${isSelected ? 'text-blue-400' : 'text-[#8b949e]'}`} />
        ) : (
          <FileText className="w-3.5 h-3.5 flex-shrink-0 text-[#8b949e]" />
        )}
        <span className="truncate">{node.name}</span>
      </div>
      {node.language && (
        <span className="text-[10px] text-[#6e7681] ml-2 flex-shrink-0">{node.language}</span>
      )}
    </div>
  )
}
