import { useState } from 'react'
import { Search, Loader2, FileCode, Tag, Sparkles, SlidersHorizontal, ArrowUpRight } from 'lucide-react'
import { repositoryApi } from '@/services/api'
import type { RetrievedChunk } from '@/types'

interface CodeSearchProps {
  repositoryId: string
  onOpenFile?: (path: string) => void
}

export function CodeSearch({ repositoryId, onOpenFile }: CodeSearchProps) {
  const [query, setQuery] = useState('')
  const [language, setLanguage] = useState<string>('')
  const [symbolType, setSymbolType] = useState<string>('')
  const [results, setResults] = useState<RetrievedChunk[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError(null)
    setSearched(true)

    try {
      const res = await repositoryApi.searchCodebase(repositoryId, {
        query: query.trim(),
        limit: 10,
        language: language || undefined,
        symbol_type: symbolType || undefined,
      })
      setResults(res.chunks)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search request failed')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Search Header Form */}
      <form onSubmit={handleSearch} className="surface p-4 space-y-3">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-[#8b949e] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search functions, classes, or ask in natural language (e.g. 'JWT token verification', 'def authenticate')..."
              className="w-full bg-[#0d1117] border border-[#30363d] rounded-md pl-9 pr-3 py-2 text-sm text-white placeholder-[#8b949e] focus:outline-none focus:border-[#388bfd]"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-5 py-2 bg-[#238636] hover:bg-[#2ea043] disabled:opacity-50 text-white text-sm font-medium rounded-md transition-colors flex items-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            Search RAG
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 text-xs text-[#8b949e] pt-1">
          <span className="flex items-center gap-1 font-medium text-white">
            <SlidersHorizontal className="w-3.5 h-3.5" /> Filters:
          </span>

          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-[#0d1117] border border-[#30363d] rounded px-2 py-1 text-xs text-[#e6edf3] focus:outline-none focus:border-[#388bfd]"
          >
            <option value="">All Languages</option>
            <option value="Python">Python</option>
            <option value="TypeScript">TypeScript</option>
            <option value="JavaScript">JavaScript</option>
            <option value="Go">Go</option>
            <option value="Rust">Rust</option>
          </select>

          <select
            value={symbolType}
            onChange={(e) => setSymbolType(e.target.value)}
            className="bg-[#0d1117] border border-[#30363d] rounded px-2 py-1 text-xs text-[#e6edf3] focus:outline-none focus:border-[#388bfd]"
          >
            <option value="">All Symbols</option>
            <option value="function">Functions</option>
            <option value="class">Classes</option>
            <option value="method">Methods</option>
            <option value="route">HTTP Routes</option>
            <option value="model">Data Models</option>
          </select>
        </div>
      </form>

      {/* Results Section */}
      {error && (
        <div className="surface p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="surface p-12 text-center text-[#8b949e] flex flex-col items-center justify-center gap-2">
          <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
          <p className="text-sm">Searching vector embeddings & symbol index...</p>
        </div>
      ) : searched && results.length === 0 ? (
        <div className="surface p-12 text-center text-[#8b949e]">
          <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-white font-medium text-sm">No matching code chunks found.</p>
          <p className="text-xs mt-1">Try broadening your query or removing language filters.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {results.map((chunk) => {
            const scorePct = Math.round(chunk.score * 100)

            return (
              <div key={chunk.id} className="surface p-4 space-y-2 hover:border-[#8b949e] transition-colors">
                {/* Chunk Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#30363d] pb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <FileCode className="w-4 h-4 text-blue-400 flex-shrink-0" />
                    <span className="font-mono text-xs font-semibold text-white">
                      {chunk.file_path}
                    </span>
                    {chunk.start_line && chunk.end_line && (
                      <span className="text-xs text-[#8b949e] font-mono">
                        L{chunk.start_line} - L{chunk.end_line}
                      </span>
                    )}
                    {chunk.symbol_name && (
                      <span className="text-[10px] bg-[#1f6feb]/20 text-blue-300 border border-blue-800 px-1.5 py-0.5 rounded font-mono flex items-center gap-1">
                        <Tag className="w-2.5 h-2.5" /> {chunk.symbol_name}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                        scorePct >= 80
                          ? 'bg-green-900/40 text-green-400 border border-green-800'
                          : scorePct >= 60
                          ? 'bg-blue-900/40 text-blue-400 border border-blue-800'
                          : 'bg-gray-800 text-gray-400 border border-gray-700'
                      }`}
                    >
                      {scorePct}% match ({chunk.match_type})
                    </span>

                    {onOpenFile && (
                      <button
                        onClick={() => onOpenFile(chunk.file_path)}
                        className="text-xs text-[#388bfd] hover:underline flex items-center gap-0.5"
                      >
                        Open File <ArrowUpRight className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Code Snippet */}
                <div className="bg-[#0d1117] p-3 rounded font-mono text-xs text-[#e6edf3] overflow-x-auto border border-[#30363d]">
                  <pre className="whitespace-pre leading-relaxed">{chunk.content}</pre>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
