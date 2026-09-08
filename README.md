# Autonomous AI Software Engineer 🤖🚀

An enterprise-grade, fully autonomous AI software engineering system capable of ingesting entire codebases, semantically indexing symbols with AST & pgvector RAG, formulating architectural plans via LangGraph, applying surgical `SEARCH/REPLACE` code modifications, executing tests in an isolated Docker sandbox with automated self-correction loops, performing security audits (OWASP), and compiling production-ready Pull Request markdown reports.

## 🏗️ Architecture & 12-Node Autonomous Workflow

1. create and paste API key in 
    1. backend\.env
    2. .env
    3. .env.example

2. Database Container (Start Docker):

    cd D:\Autonomous_AI_Software_Engineer

    docker compose up -d postgres

3. FastAPI Backend API:

    cd D:\Autonomous_AI_Software_Engineer\backend

    python -m uvicorn app.main:app --reload --port 8000

4. React Frontend UI:

    cd D:\Autonomous_AI_Software_Engineer\frontend

    npm run dev

## 📄 License
MIT License. Built with ❤️ by the Autonomous AI Engineering Team.
