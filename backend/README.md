# Autonomous AI Software Engineer — Backend ⚙️

The core intelligence and orchestration backend for the Autonomous AI Software Engineer, powered by **FastAPI**, **LangGraph**, **PostgreSQL + pgvector**, and an isolated **Docker Sandbox**.

---

## 🧠 System Architecture

The backend implements an autonomous agentic loop designed to tackle software engineering tasks end-to-end:

```
                  ┌───────────────────────────────┐
                  │       Repository Ingest       │
                  │   (AST Parser & Vector RAG)   │
                  └───────────────┬───────────────┘
                                  ▼
                  ┌───────────────────────────────┐
                  │    Architectural Planner      │
                  │      (Task Decomposition)     │
                  └───────────────┬───────────────┘
                                  ▼
                  ┌───────────────────────────────┐
                  │        Code Editor            │
                  │   (Surgical Search/Replace)   │
                  └───────────────┬───────────────┘
                                  ▼
┌──────────────┐  ┌───────────────────────────────┐
│ Self-Correct │◄─┤     Isolated Docker Sandbox   │
│  Debugger    │  │       (Test Execution)        │
└──────┬───────┘  └───────────────┬───────────────┘
       │                          │ (Passing)
       └─────────────────────────►▼
                  ┌───────────────────────────────┐
                  │    Security Auditor (OWASP)   │
                  └───────────────┬───────────────┘
                                  ▼
                  ┌───────────────────────────────┐
                  │      PR Markdown Report       │
                  └───────────────────────────────┘
```

---

## 🛠️ Tech Stack

* **Framework**: FastAPI (Python 3.11+)
* **Agent Orchestration**: LangGraph, LangChain
* **LLM Engine**: OpenAI (GPT-4o), OpenAI-compatible, or local LLMs
* **Vector Store & DB**: PostgreSQL 16 + pgvector, SQLAlchemy (asyncio), AsyncPG
* **Database Migrations**: Alembic
* **Sandboxing**: Docker Engine API
* **Security & Auth**: python-jose, passlib

---

## 🚀 Getting Started

### 1. Requirements
* Python 3.11+
* Docker Desktop running (for PostgreSQL + pgvector)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Initialization
Start the PostgreSQL container:
```bash
docker compose up -d postgres
```

Run database migrations:
```bash
alembic upgrade head
```

### 4. Run Development Server
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

* **Interactive API Documentation**: http://localhost:8000/docs
* **Health Check**: http://localhost:8000/health
