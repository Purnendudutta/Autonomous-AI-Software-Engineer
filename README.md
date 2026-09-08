# Autonomous AI Software Engineer 🤖🚀

An enterprise-grade, fully autonomous AI software engineering system capable of ingesting entire codebases, semantically indexing symbols with AST & pgvector RAG, formulating architectural plans via LangGraph, applying surgical `SEARCH/REPLACE` code modifications, executing tests in an isolated Docker sandbox with automated self-correction loops, performing security audits (OWASP), and compiling production-ready Pull Request markdown reports.



#                                                                             env
# Application
APP_NAME="Autonomous AI Software Engineer"
APP_VERSION="0.1.0"
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production-12345678
# API
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
# Database (Default to localhost for local testing, overridden to postgres in docker-compose)
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=ai_engineer
POSTGRES_USER=ai_engineer
POSTGRES_PASSWORD=changeme
# LLM Provider Configuration (Google Gemini)
LLM_PROVIDER=openai
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-3.6-flash
OPENAI_API_KEY=API_KEY_IS HERE
# Embedding Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=gemini-embedding-2
EMBEDDING_DIMENSIONS=1536
EMBEDDING_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
# Workspaces
WORKSPACE_BASE_DIR=/tmp/ai-engineer-workspaces



#                                                                   env-example
#  Autonomous AI Software Engineer — Environment Configuration
#  Copy this file to .env and fill in real values.
#  NEVER commit .env to version control.
# ─── Application ─────────────────────────────────────────────────────────────
APP_NAME="Autonomous AI Software Engineer"
APP_VERSION="0.1.0"
ENVIRONMENT=development          # development | production
DEBUG=true
SECRET_KEY=change-me-to-a-random-64-char-string
# ─── API ─────────────────────────────────────────────────────────────────────
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
# ─── Database ────────────────────────────────────────────────────────────────
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=ai_engineer
POSTGRES_USER=ai_engineer
POSTGRES_PASSWORD=change-me-strong-password
# Constructed automatically from above — override if needed
# DATABASE_URL=postgresql+asyncpg://ai_engineer:password@postgres:5432/ai_engineer
# ─── LLM Provider ────────────────────────────────────────────────────────────
# Supported: openai | openai_compatible | local
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4096
# OpenAI-compatible endpoint (leave empty for official OpenAI)
LLM_BASE_URL=
# API key — required for openai and openai_compatible providers
OPENAI_API_KEY=your_api_key_here
# ─── Embedding Model ─────────────────────────────────────────────────────────
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
# ─── GitHub ──────────────────────────────────────────────────────────────────
# Personal access token for cloning private repos and GitHub API calls
# Scopes needed: repo, read:org (optional)
GITHUB_TOKEN=
# ─── Agent / Sandbox ─────────────────────────────────────────────────────────
# Maximum retry attempts for the fix→test→analyze loop
MAX_RETRIES=3
# Docker sandbox resource limits
SANDBOX_CPU_QUOTA=50000          # 50% of one CPU (microseconds per 100ms period)
SANDBOX_MEMORY_MB=512            # MB
SANDBOX_TIMEOUT_SECONDS=120      # Wall-clock timeout for test execution
SANDBOX_NETWORK_DISABLED=true
# Maximum repository size in MB (reject repos larger than this)
MAX_REPO_SIZE_MB=500
# Maximum file size in KB for indexing
MAX_FILE_SIZE_KB=512
# Maximum agent iterations (hard stop)
MAX_AGENT_ITERATIONS=50
# Maximum tool calls per agent run
MAX_TOOL_CALLS=200
# ─── Workspaces
# Base directory for temporary repository workspaces
WORKSPACE_BASE_DIR=/tmp/ai-engineer-workspaces
# ─── Frontend
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME="AI Software Engineer"



#                                                                       env(backend)
# Application
APP_NAME="Autonomous AI Software Engineer"
APP_VERSION="0.1.0"
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production-12345678

# API
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Database (Default to localhost for local testing, overridden to postgres in docker-compose)
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=ai_engineer
POSTGRES_USER=ai_engineer
POSTGRES_PASSWORD=changeme

# LLM Provider Configuration (Google Gemini)
LLM_PROVIDER=openai
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-3.6-flash
OPENAI_API_KEY=API_KEY_GOES_HERE

# Embedding Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=gemini-embedding-2
EMBEDDING_DIMENSIONS=1536
EMBEDDING_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/

# Workspaces
WORKSPACE_BASE_DIR=/tmp/ai-engineer-workspaces



## 📄 License
MIT License. Built with ❤️ by the Autonomous AI Engineering Team.
