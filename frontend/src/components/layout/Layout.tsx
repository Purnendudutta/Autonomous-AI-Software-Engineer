import { ReactNode } from 'react'
import { Github, ExternalLink } from 'lucide-react'
import { Sidebar } from './Sidebar'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-[#0d1117] flex text-[#e6edf3]">
      <Sidebar />
      <main className="flex-1 ml-60 p-6 pb-16 overflow-x-hidden min-h-screen">
        {children}
      </main>

      {/* Creator Attribution Button (Bottom-Right Corner) */}
      <a
        href="https://github.com/Purnendudutta"
        target="_blank"
        rel="noopener noreferrer"
        className="fixed bottom-4 right-4 z-50 flex items-center gap-2 px-3.5 py-2 rounded-full bg-[#161b22]/90 backdrop-blur-md border border-[#30363d] hover:border-[#58a6ff] text-xs font-medium text-[#c9d1d9] hover:text-white shadow-lg hover:shadow-[#58a6ff]/10 transition-all duration-200 group"
        title="Visit Purnendu Dutta's GitHub Profile"
      >
        <Github className="w-4 h-4 text-[#8b949e] group-hover:text-white transition-colors" />
        <span>
          Created by <span className="font-semibold text-white group-hover:text-[#58a6ff] transition-colors">Purnendu Dutta</span>
        </span>
        <ExternalLink className="w-3 h-3 text-[#6e7681] group-hover:text-[#58a6ff] transition-colors" />
      </a>
    </div>
  )
}

