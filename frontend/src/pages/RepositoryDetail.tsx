import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  GitBranch,
  FileCode2,
  Cpu,
  Layers,
  Clock,
  Plus,
  Loader2,
  AlertCircle,
  FileText,
  Search,
  Sparkles,
} from 'lucide-react'
import { repositoryApi } from '@/services/api'
import { FileTree } from '@/components/FileTree'
import { CodeSearch } from '@/components/CodeSearch'
import type { FileContentResponse, FileTreeNode, RepositorySnapshot, Repository } from '@/types'

const LANG_COLORS: Record<string, string> = {
  Python: 'bg-blue-500',
  TypeScript: 'bg-blue-600',
  JavaScript: 'bg-yellow-400 text-black',
  HTML: 'bg-orange-500',
  CSS: 'bg-purple-500',
  Rust: 'bg-amber-700',
  Go: 'bg-cyan-500',
  Docker: 'bg-sky-500',
  Shell: 'bg-emerald-500',
}

export function RepositoryDetail() {
  const { repoId } = useParams<{ repoId: string }>()
  const [repo, setRepo] = useState<Repository | null>(null)
  const [snapshot, setSnapshot] = useState<RepositorySnapshot | null>(null)
  const [tree, setTree] = useState<FileTreeNode | null>(null)
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<FileContentResponse | null>(null)
  const [activeTab, setActiveTab] = useState<'files' | 'search'>('files')
  const [indexing, setIndexing] = useState(false)
  const [indexSuccess, setIndexSuccess] = useState(false)
  const [loading, setLoading] = useState(true)
  const [fileLoading, setFileLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadRepositoryData() {
      if (!repoId) return
      setLoading(true)
      setError(null)
      try {
        const [repoData, snapData, treeData] = await Promise.all([
          repositoryApi.get(repoId),
          repositoryApi.getSnapshot(repoId).catch(() => null),
          repositoryApi.getTree(repoId).catch(() => null),
        ])
        setRepo(repoData)
        setSnapshot(snapData)
        setTree(treeData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load repository details')
      } finally {
        setLoading(false)
      }
    }
    loadRepositoryData()
  }, [repoId])

  const handleSelectFile = async (path: string) => {
    if (!repoId || !path) return
    setSelectedFilePath(path)
    setActiveTab('files')
    setFileLoading(true)
    try {
      const data = await repositoryApi.getFileContent(repoId, path)
      setFileContent(data)
    } catch {
      setFileContent(null)
    } finally {
      setFileLoading(false)
    }
  }

  const handleTriggerIndex = async () => {
    if (!repoId) return
    setIndexing(true)
    setIndexSuccess(false)
    try {
      await repositoryApi.indexRepository(repoId)
      setIndexSuccess(true)
      setTimeout(() => setIndexSuccess(false), 4000)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Indexing failed')
    } finally {
      setIndexing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-[#8b949e] gap-3">
        <Loader2 className="w-5 h-5 animate-spin" />
        Loading repository intelligence...
      </div>
    )
  }

  if (error || !repo) {
    return (
      <div className="surface p-6 max-w-2xl mx-auto">
        <AlertCircle className="w-8 h-8 text-red-400 mb-2" />
        <h2 className="text-lg font-bold text-white mb-1">Repository Load Error</h2>
        <p className="text-sm text-[#8b949e] mb-4">{error || 'Repository not found'}</p>
        <Link to="/repositories" className="text-sm text-[#388bfd] hover:underline">
          ← Back to Repositories
        </Link>
      </div>
    )
  }

  const languages = snapshot?.languages ? Object.values(snapshot.languages) : []
  const frameworks = snapshot?.frameworks || []

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 surface p-5">
        <div>
          <div className="flex items-center gap-2 text-xs text-[#8b949e] mb-1">
            <Link to="/repositories" className="hover:text-white transition-colors">
              Repositories
            </Link>
            <span>/</span>
            <span>{repo.owner}</span>
          </div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <GitBranch className="w-6 h-6 text-green-400" />
            {repo.owner}/{repo.name}
          </h1>
          <p className="text-xs text-[#8b949e] mt-1 font-mono">{repo.url}</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleTriggerIndex}
            disabled={indexing}
            className="px-3.5 py-2 bg-[#21262d] hover:bg-[#30363d] text-white text-xs font-medium rounded-md transition-colors flex items-center gap-1.5 border border-[#30363d]"
          >
            {indexing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            )}
            {indexing ? 'Re-indexing...' : indexSuccess ? 'Indexing Started!' : 'Re-index RAG'}
          </button>

          <Link
            to="/tasks"
            className="px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white text-xs font-medium rounded-md transition-colors flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            Assign Agent Task
          </Link>
        </div>
      </div>

      {/* Snapshot Architecture Summary Cards */}
      {snapshot && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="surface p-4">
            <p className="text-xs text-[#8b949e] flex items-center gap-1.5 mb-1">
              <Cpu className="w-3.5 h-3.5" /> Total Files & LOC
            </p>
            <p className="text-lg font-bold text-white">
              {snapshot.file_count?.toLocaleString()} files
            </p>
            <p className="text-xs text-[#8b949e] mt-0.5">
              {(snapshot.total_size_bytes ? snapshot.total_size_bytes / (1024 * 1024) : 0).toFixed(2)} MB
            </p>
          </div>

          <div className="surface p-4">
            <p className="text-xs text-[#8b949e] flex items-center gap-1.5 mb-1">
              <GitBranch className="w-3.5 h-3.5" /> Commit & Branch
            </p>
            <p className="text-lg font-bold text-white font-mono text-sm">
              {snapshot.commit_sha.slice(0, 8)}
            </p>
            <p className="text-xs text-[#8b949e] mt-0.5">
              branch: <span className="text-blue-400">{snapshot.branch || 'main'}</span>
            </p>
          </div>

          <div className="surface p-4">
            <p className="text-xs text-[#8b949e] flex items-center gap-1.5 mb-1">
              <Layers className="w-3.5 h-3.5" /> Frameworks
            </p>
            <div className="flex flex-wrap gap-1 mt-1">
              {frameworks.length > 0 ? (
                frameworks.map((f, i) => (
                  <span
                    key={i}
                    className="text-[10px] bg-[#1f6feb]/20 text-blue-300 border border-blue-800 px-1.5 py-0.5 rounded"
                  >
                    {f.name}
                  </span>
                ))
              ) : (
                <span className="text-xs text-[#8b949e]">Standard library</span>
              )}
            </div>
          </div>

          <div className="surface p-4">
            <p className="text-xs text-[#8b949e] flex items-center gap-1.5 mb-1">
              <Clock className="w-3.5 h-3.5" /> Indexed Status
            </p>
            <p className="text-xs text-white mt-1">
              {snapshot.indexed_at ? new Date(snapshot.indexed_at).toLocaleTimeString() : 'Not indexed yet'}
            </p>
            <p className="text-[11px] text-green-400 mt-1">pgvector Vector Store Ready</p>
          </div>
        </div>
      )}

      {/* Language Breakdown Bar */}
      {languages.length > 0 && (
        <div className="surface p-4">
          <h2 className="text-xs font-semibold text-[#8b949e] uppercase tracking-wider mb-2">
            Language Composition
          </h2>
          <div className="w-full h-3 rounded-full overflow-hidden flex bg-[#21262d] mb-3">
            {languages.map((l, i) => (
              <div
                key={i}
                style={{ width: `${Math.max(2, l.percentage)}%` }}
                className={`${LANG_COLORS[l.name] || 'bg-gray-500'}`}
                title={`${l.name}: ${l.percentage}% (${l.lines_of_code} LOC)`}
              />
            ))}
          </div>
          <div className="flex flex-wrap gap-4 text-xs">
            {languages.map((l, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <span className={`w-2.5 h-2.5 rounded-full ${LANG_COLORS[l.name] || 'bg-gray-500'}`} />
                <span className="font-medium text-white">{l.name}</span>
                <span className="text-[#8b949e]">{l.percentage}%</span>
                <span className="text-[#6e7681]">({l.lines_of_code.toLocaleString()} lines)</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* View Switcher Tabs */}
      <div className="flex items-center gap-2 border-b border-[#30363d] pb-2">
        <button
          onClick={() => setActiveTab('files')}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
            activeTab === 'files'
              ? 'bg-[#21262d] text-white border border-[#30363d]'
              : 'text-[#8b949e] hover:text-white'
          }`}
        >
          <FileCode2 className="w-4 h-4 text-blue-400" />
          Codebase Files & Summary
        </button>

        <button
          onClick={() => setActiveTab('search')}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
            activeTab === 'search'
              ? 'bg-[#21262d] text-white border border-[#30363d]'
              : 'text-[#8b949e] hover:text-white'
          }`}
        >
          <Search className="w-4 h-4 text-green-400" />
          Semantic Code Search (RAG)
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'search' && repoId ? (
        <CodeSearch repositoryId={repoId} onOpenFile={handleSelectFile} />
      ) : (
        /* Explorer Split View (File Tree & Content / Summary) */
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 min-h-[500px]">
          {/* Left: File Tree Explorer */}
          <div className="md:col-span-4 surface p-3 flex flex-col max-h-[700px] overflow-hidden">
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-[#30363d] px-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-[#8b949e] flex items-center gap-1.5">
                <FileCode2 className="w-3.5 h-3.5 text-blue-400" />
                Codebase Files
              </h3>
              {tree && (
                <button
                  onClick={() => setSelectedFilePath(null)}
                  className="text-[11px] text-[#388bfd] hover:underline"
                >
                  View Summary
                </button>
              )}
            </div>
            <div className="flex-1 overflow-y-auto pr-1">
              {tree ? (
                <FileTree
                  node={tree}
                  onSelectFile={handleSelectFile}
                  selectedPath={selectedFilePath || undefined}
                />
              ) : (
                <p className="text-xs text-[#8b949e] p-4 text-center">No file tree available.</p>
              )}
            </div>
          </div>

          {/* Right: File Viewer or Architecture Summary */}
          <div className="md:col-span-8 surface p-5 flex flex-col max-h-[700px] overflow-hidden">
            {selectedFilePath ? (
              <div className="flex flex-col h-full">
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#30363d]">
                  <div className="flex items-center gap-2 font-mono text-xs text-white truncate">
                    <FileText className="w-4 h-4 text-blue-400 flex-shrink-0" />
                    <span className="truncate">{selectedFilePath}</span>
                  </div>
                  {fileContent && (
                    <span className="text-[11px] text-[#8b949e] flex-shrink-0">
                      {fileContent.language} · {(fileContent.size_bytes / 1024).toFixed(1)} KB
                    </span>
                  )}
                </div>

                <div className="flex-1 overflow-auto font-mono text-xs bg-[#0d1117] p-4 rounded border border-[#30363d] text-[#e6edf3]">
                  {fileLoading ? (
                    <div className="flex items-center gap-2 text-[#8b949e]">
                      <Loader2 className="w-4 h-4 animate-spin" /> Loading file content...
                    </div>
                  ) : fileContent ? (
                    <pre className="leading-relaxed whitespace-pre-wrap">{fileContent.content}</pre>
                  ) : (
                    <p className="text-[#8b949e]">Unable to preview file.</p>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto prose prose-invert max-w-none text-xs text-[#e6edf3]">
                {snapshot?.summary ? (
                  <div className="space-y-3">
                    <pre className="font-sans whitespace-pre-wrap leading-relaxed text-sm bg-transparent p-0 border-none text-[#e6edf3]">
                      {snapshot.summary}
                    </pre>
                  </div>
                ) : (
                  <div className="text-center py-20 text-[#8b949e]">
                    <Layers className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>Select a file from the tree to view its contents.</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
