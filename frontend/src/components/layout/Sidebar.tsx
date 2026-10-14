import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  GitBranch,
  ListTodo,
  Bot,
} from 'lucide-react'
import { clsx } from 'clsx'

const navItems = [
  { path: '/', label: 'Overview Dashboard', icon: LayoutDashboard },
  { path: '/repositories', label: 'Repositories & RAG', icon: GitBranch },
  { path: '/tasks', label: 'Engineering Tasks', icon: ListTodo },
] as const

export function Sidebar() {
  const location = useLocation()

  return (
    <aside className="fixed inset-y-0 left-0 w-60 bg-[#161b22] border-r border-[#30363d] flex flex-col z-10 select-none">
      {/* Brand Header */}
      <div className="flex items-center gap-3 px-4 py-4 border-b border-[#30363d]">
        <div className="w-8 h-8 rounded-lg bg-green-950/60 border border-green-700 flex items-center justify-center flex-shrink-0">
          <Bot className="w-5 h-5 text-green-400" />
        </div>
        <div>
          <span className="font-bold text-sm text-white leading-tight block">
            AI Engineer
          </span>
          <span className="text-[10px] text-green-400 font-mono flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            Autonomous Agent
          </span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 overflow-y-auto py-4">
        <div className="px-3 mb-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-[#8b949e] px-2 mb-2">
            Main Workspace
          </p>
          {navItems.map(({ path, label, icon: Icon }) => (
            <Link
              key={path}
              to={path}
              className={clsx(
                'flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium transition-all mb-1',
                location.pathname === path
                  ? 'bg-[#1f6feb] text-white shadow-sm font-semibold'
                  : 'text-[#8b949e] hover:text-white hover:bg-[#21262d]',
              )}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </Link>
          ))}
        </div>
      </nav>
    </aside>
  )
}

