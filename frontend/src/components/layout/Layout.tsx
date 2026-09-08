import { ReactNode } from 'react'
import { Sidebar } from './Sidebar'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-[#0d1117] flex text-[#e6edf3]">
      <Sidebar />
      <main className="flex-1 ml-60 p-6 overflow-x-hidden min-h-screen">
        {children}
      </main>
    </div>
  )
}
