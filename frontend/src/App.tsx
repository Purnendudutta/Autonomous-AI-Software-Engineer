import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { Repositories } from '@/pages/Repositories'
import { RepositoryDetail } from '@/pages/RepositoryDetail'
import { Tasks } from '@/pages/Tasks'
import { TaskDetail } from '@/pages/TaskDetail'
import { CodeChanges } from '@/pages/CodeChanges'
import { TestResults } from '@/pages/TestResults'
import { CodeReview } from '@/pages/CodeReview'
import { Report } from '@/pages/Report'

export function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/repositories" element={<Repositories />} />
          <Route path="/repositories/:repoId" element={<RepositoryDetail />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/tasks/:taskId" element={<TaskDetail />} />
          <Route path="/tasks/:taskId/changes" element={<CodeChanges />} />
          <Route path="/tasks/:taskId/tests" element={<TestResults />} />
          <Route path="/tasks/:taskId/review" element={<CodeReview />} />
          <Route path="/tasks/:taskId/report" element={<Report />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
