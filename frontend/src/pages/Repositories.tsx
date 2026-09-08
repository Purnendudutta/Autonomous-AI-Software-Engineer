import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { GitBranch, Plus, Loader2, AlertCircle, ArrowRight, Layers, FileCode2, Clock } from 'lucide-react'
import { repositoryApi } from '@/services/api'
import type { Repository } from '@/types'

export function Repositories() {
  const [repos, setRepos] = useState<Repository[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [url, setUrl] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const fetchRepos = async () => {
    try {
      const data = await repositoryApi.list()
      setRepos(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load repositories')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRepos()
  }, [])

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      await repositoryApi.analyze({ url: url.trim() })
      setUrl('')
      // Poll after 2 seconds to pick up latest analyzed snapshot
      setTimeout(() => {
        fetchRepos()
      }, 2500)
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to analyze repository')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Repository Ingestion & Analysis</h1>
        <p className="text-[#8b949e] mt-1">
          Connect GitHub repositories to automatically parse architecture, detect frameworks, and index source code
        </p>
      </div>

      {/* Ingest Repository Form */}
      <div className="surface p-5">
        <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
          <Plus className="w-4 h-4 text-green-400" /> Ingest New GitHub Repository
        </h2>
        <form onSubmit={handleAnalyze} className="flex flex-col sm:flex-row gap-2">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/owner/repository"
            className="flex-1 bg-[#0d1117] border border-[#30363d] rounded-md px-3 py-2 text-sm text-white placeholder-[#8b949e] focus:outline-none focus:border-[#388bfd]"
          />
          <button
            type="submit"
            disabled={submitting || !url.trim()}
            className="px-5 py-2 bg-[#238636] hover:bg-[#2ea043] disabled:opacity-50 text-white text-sm font-medium rounded-md transition-colors flex items-center justify-center gap-2"
          >
            {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
            {submitting ? 'Cloning & Analyzing...' : 'Analyze Codebase'}
          </button>
        </form>
        {submitError && (
          <p className="mt-2 text-sm text-red-400 flex items-center gap-1">
            <AlertCircle className="w-4 h-4" /> {submitError}
          </p>
        )}
      </div>

      {/* Repositories List */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
          <GitBranch className="w-5 h-5" /> Analyzed Repositories ({repos.length})
        </h2>

        {loading ? (
          <div className="flex items-center gap-2 text-[#8b949e] py-6">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading repositories...
          </div>
        ) : error ? (
          <p className="text-red-400 text-sm">{error}</p>
        ) : repos.length === 0 ? (
          <div className="surface p-12 text-center">
            <GitBranch className="w-10 h-10 text-[#8b949e] mx-auto mb-3 opacity-60" />
            <p className="text-white font-medium text-sm">No repositories analyzed yet.</p>
            <p className="text-[#8b949e] text-xs mt-1">
              Enter a GitHub URL above to clone and explore its architecture.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {repos.map((repo) => {
              const snapshot = repo.latest_snapshot
              const frameworks = snapshot?.frameworks || []

              return (
                <div
                  key={repo.id}
                  className="surface p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-[#8b949e] transition-colors"
                >
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="text-base font-bold text-white">
                        {repo.owner}/{repo.name}
                      </h3>
                      <span className="text-xs bg-[#21262d] text-[#8b949e] px-2 py-0.5 rounded-full font-mono">
                        {repo.default_branch || 'main'}
                      </span>
                      {snapshot && (
                        <span className="text-xs bg-green-900/30 text-green-400 border border-green-800 px-2 py-0.5 rounded-full font-medium">
                          Analyzed
                        </span>
                      )}
                    </div>

                    <a
                      href={repo.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-[#388bfd] hover:underline block font-mono"
                    >
                      {repo.url}
                    </a>

                    {snapshot ? (
                      <div className="flex flex-wrap items-center gap-4 text-xs text-[#8b949e] pt-1">
                        <span className="flex items-center gap-1">
                          <FileCode2 className="w-3.5 h-3.5 text-blue-400" />
                          {snapshot.file_count?.toLocaleString()} files
                        </span>
                        {frameworks.length > 0 && (
                          <span className="flex items-center gap-1">
                            <Layers className="w-3.5 h-3.5 text-purple-400" />
                            {frameworks.slice(0, 3).map((f) => f.name).join(', ')}
                            {frameworks.length > 3 && ` +${frameworks.length - 3}`}
                          </span>
                        )}
                        <span className="flex items-center gap-1 font-mono text-[11px]">
                          <Clock className="w-3 h-3" />
                          commit: {snapshot.commit_sha.slice(0, 7)}
                        </span>
                      </div>
                    ) : (
                      <p className="text-xs text-[#8b949e] italic">Analysis pending...</p>
                    )}
                  </div>

                  <div>
                    <Link
                      to={`/repositories/${repo.id}`}
                      className="px-4 py-2 bg-[#21262d] hover:bg-[#30363d] text-white text-xs font-medium rounded-md transition-colors inline-flex items-center gap-1.5"
                    >
                      Explore Codebase <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
