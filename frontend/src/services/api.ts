/**
 * Typed API client for the AI Software Engineer backend.
 *
 * All API calls go through this module — no raw fetch/axios in components.
 */

import axios, { AxiosError } from 'axios'
import type {
  AnalyzeRepositoryRequest,
  CodeReview,
  CodeSearchRequest,
  CodeSearchResponse,
  CreateTaskRequest,
  DiffResponse,
  FileContentResponse,
  FileTreeNode,
  HealthResponse,
  IndexStatusResponse,
  Report,
  Repository,
  RepositorySnapshot,
  Task,
  TaskStatusResponse,
  TestRun,
} from '@/types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 45_000,
})

// ─── Response interceptor for error normalisation ─────────────────────────────

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const detail =
      (error.response?.data as { detail?: string })?.detail ||
      error.message ||
      'An unexpected error occurred'
    return Promise.reject(new Error(detail))
  },
)

// ─── Health ───────────────────────────────────────────────────────────────────

export const healthApi = {
  check: async (): Promise<HealthResponse> => {
    const { data } = await apiClient.get<HealthResponse>('/health')
    return data
  },
}

// ─── Repositories & RAG ───────────────────────────────────────────────────────

export const repositoryApi = {
  analyze: async (request: AnalyzeRepositoryRequest): Promise<Task> => {
    const { data } = await apiClient.post<Task>('/api/repositories/analyze', request)
    return data
  },

  list: async (): Promise<Repository[]> => {
    const { data } = await apiClient.get<Repository[]>('/api/repositories')
    return data
  },

  get: async (id: string): Promise<Repository> => {
    const { data } = await apiClient.get<Repository>(`/api/repositories/${id}`)
    return data
  },

  getSnapshot: async (id: string): Promise<RepositorySnapshot> => {
    const { data } = await apiClient.get<RepositorySnapshot>(`/api/repositories/${id}/snapshot`)
    return data
  },

  getTree: async (id: string): Promise<FileTreeNode> => {
    const { data } = await apiClient.get<FileTreeNode>(`/api/repositories/${id}/tree`)
    return data
  },

  getFileContent: async (id: string, path: string): Promise<FileContentResponse> => {
    const { data } = await apiClient.get<FileContentResponse>(`/api/repositories/${id}/file`, {
      params: { path },
    })
    return data
  },

  indexRepository: async (repositoryId: string): Promise<IndexStatusResponse> => {
    const { data } = await apiClient.post<IndexStatusResponse>(`/api/repositories/${repositoryId}/index`)
    return data
  },

  searchCodebase: async (repositoryId: string, request: CodeSearchRequest): Promise<CodeSearchResponse> => {
    const { data } = await apiClient.post<CodeSearchResponse>(`/api/repositories/${repositoryId}/search`, request)
    return data
  },
}

// ─── Tasks ────────────────────────────────────────────────────────────────────

export const taskApi = {
  list: async (repositoryId?: string): Promise<Task[]> => {
    const { data } = await apiClient.get<Task[]>('/api/tasks', {
      params: repositoryId ? { repository_id: repositoryId } : {},
    })
    return data
  },

  create: async (request: CreateTaskRequest): Promise<Task> => {
    const { data } = await apiClient.post<Task>('/api/tasks', request)
    return data
  },

  get: async (taskId: string): Promise<Task> => {
    const { data } = await apiClient.get<Task>(`/api/tasks/${taskId}`)
    return data
  },

  getStatus: async (taskId: string): Promise<TaskStatusResponse> => {
    const { data } = await apiClient.get<TaskStatusResponse>(`/api/tasks/${taskId}/status`)
    return data
  },

  getDiff: async (taskId: string): Promise<DiffResponse> => {
    const { data } = await apiClient.get<DiffResponse>(`/api/tasks/${taskId}/diff`)
    return data
  },

  getTests: async (taskId: string): Promise<TestRun[]> => {
    const { data } = await apiClient.get<TestRun[]>(`/api/tasks/${taskId}/tests`)
    return data
  },

  getReview: async (taskId: string): Promise<CodeReview> => {
    const { data } = await apiClient.get<CodeReview>(`/api/tasks/${taskId}/review`)
    return data
  },

  getReport: async (taskId: string): Promise<Report> => {
    const { data } = await apiClient.get<Report>(`/api/tasks/${taskId}/report`)
    return data
  },

  cancel: async (taskId: string): Promise<{ task_id: string; status: string; message: string }> => {
    const { data } = await apiClient.post(`/api/tasks/${taskId}/cancel`)
    return data
  },

  getLogsUrl: (taskId: string): string => `${BASE_URL}/api/tasks/${taskId}/logs`,
}

export default apiClient
