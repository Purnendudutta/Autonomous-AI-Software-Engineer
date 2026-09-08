/**
 * TypeScript types mirroring backend Pydantic schemas.
 * Keep in sync with backend/app/schemas/
 */

// ─── Repository ───────────────────────────────────────────────────────────────

export interface LanguageStat {
  name: string
  file_count: number
  lines_of_code: number
  percentage: number
}

export interface FrameworkInfo {
  name: string
  category: string
  version?: string | null
  config_file?: string | null
}

export interface FileTreeNode {
  name: string
  path: string
  is_dir: boolean
  size_bytes: number
  extension?: string | null
  language?: string | null
  children?: FileTreeNode[] | null
}

export interface FileContentResponse {
  path: string
  filename: string
  size_bytes: number
  language?: string | null
  content: string
  is_truncated: boolean
}

export interface RepositorySnapshot {
  id: string
  repository_id: string
  commit_sha: string
  branch: string | null
  workspace_path?: string | null
  languages: Record<string, LanguageStat> | null
  frameworks: FrameworkInfo[] | null
  file_count: number | null
  total_size_bytes: number | null
  summary: string | null
  indexed_at: string | null
  created_at: string
}

export interface Repository {
  id: string
  url: string
  owner: string
  name: string
  default_branch: string | null
  is_private: boolean
  created_at: string
  updated_at: string
  latest_snapshot?: RepositorySnapshot | null
}

export interface AnalyzeRepositoryRequest {
  url: string
  branch?: string
  commit_sha?: string
  task_description?: string
}

// ─── Code Search / RAG ────────────────────────────────────────────────────────

export interface CodeSearchRequest {
  query: string
  limit?: number
  similarity_threshold?: number
  language?: string
  symbol_type?: string
  file_path_prefix?: string
}

export interface RetrievedChunk {
  id: string
  file_path: string
  language?: string | null
  symbol_type?: string | null
  symbol_name?: string | null
  start_line?: number | null
  end_line?: number | null
  content: string
  score: number
  match_type: 'semantic' | 'exact_symbol' | 'keyword'
  metadata?: Record<string, unknown> | null
}

export interface CodeSearchResponse {
  query: string
  repository_id: string
  snapshot_id: string
  total_matches: number
  chunks: RetrievedChunk[]
  searched_at: string
}

export interface IndexStatusResponse {
  repository_id: string
  snapshot_id: string
  status: 'pending' | 'indexing' | 'completed' | 'failed'
  total_files_indexed: number
  total_chunks_created: number
  error_message?: string | null
  indexed_at?: string | null
}

// ─── Agent & Planning ─────────────────────────────────────────────────────────

export interface PlanStep {
  step_number: number
  action: 'read_file' | 'modify_code' | 'create_file' | 'run_tests' | 'verify' | string
  target_file: string
  description: string
  rationale: string
  status?: 'pending' | 'in_progress' | 'completed' | 'failed'
}

export interface ExecutionPlan {
  task_type: string
  root_cause_analysis?: string | null
  architecture_overview?: string | null
  target_files: string[]
  steps: PlanStep[]
  test_strategy: string[]
  verification_criteria: string[]
}

export interface AgentStep {
  id: string
  sequence: number
  node_name: string
  tool_name: string | null
  input_summary: string | null
  output_summary: string | null
  status: 'running' | 'completed' | 'failed'
  error: string | null
  duration_ms: number | null
  created_at: string
}

export interface AgentLogEvent {
  event_type: string
  task_id: string
  sequence: number
  node_name: string
  tool_name?: string
  message: string
  status: string
  timestamp: string
}

export interface DiffResponse {
  task_id: string
  diff: string
  files_changed: string[]
  lines_added: number
  lines_removed: number
  generated_at: string
}

// ─── Task ─────────────────────────────────────────────────────────────────────

export type TaskStatus =
  | 'pending'
  | 'running'
  | 'succeeded'
  | 'partial_success'
  | 'failed'
  | 'blocked'
  | 'cancelled'

export interface Task {
  id: string
  repository_id: string
  snapshot_id: string | null
  description: string
  status: TaskStatus
  branch: string | null
  target_commit: string | null
  retry_count: number
  error_message: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  execution_plan?: ExecutionPlan | null
}

export interface CreateTaskRequest {
  repository_id: string
  description: string
  branch?: string
  target_commit?: string
}

export interface TaskStatusResponse {
  task_id: string
  status: TaskStatus
  retry_count: number
  current_step: string | null
  progress_percent: number | null
  error_message: string | null
}

// ─── Test Results ─────────────────────────────────────────────────────────────

export type TestResultStatus = 'passed' | 'failed' | 'skipped' | 'error'

export interface TestResultItem {
  test_name: string
  test_file: string | null
  status: TestResultStatus
  duration_seconds: number | null
  failure_message: string | null
}

export interface TestRun {
  id: string
  task_id: string
  attempt_number: number
  command: string | null
  exit_code: number | null
  stdout: string | null
  stderr: string | null
  duration_seconds: number | null
  timed_out: boolean
  tests_total: number | null
  tests_passed: number | null
  tests_failed: number | null
  tests_skipped: number | null
  results: TestResultItem[]
  created_at: string
}

// ─── Code Review ──────────────────────────────────────────────────────────────

export type ReviewSeverity = 'high' | 'medium' | 'low' | 'info'

export interface ReviewFinding {
  id: string
  severity: ReviewSeverity
  category: string
  file_path: string | null
  line_number: number | null
  issue: string
  recommendation: string | null
  created_at: string
}

export interface CodeReview {
  task_id: string
  findings: ReviewFinding[]
  high_count: number
  medium_count: number
  low_count: number
  info_count: number
  generated_at: string
}

export type CodeReviewResponse = CodeReview
export type ReviewFindingResponse = ReviewFinding

// ─── Report ───────────────────────────────────────────────────────────────────

export type VerificationStatus = 'SUCCESS' | 'PARTIAL_SUCCESS' | 'FAILED' | 'BLOCKED' | 'pending'

export interface Report {
  id: string
  task_id: string
  title: string
  summary: string | null
  problem_description: string | null
  root_cause: string | null
  changes_description: string | null
  verification_status: VerificationStatus
  git_diff: string | null
  full_report_markdown: string | null
  created_at: string
}

export type ReportResponse = Report

// ─── Health ───────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: 'ok' | 'degraded'
  version: string
  environment: string
  db: string
  llm_provider: string
  llm_model: string
  timestamp: string
}
