# Start all services for the Autonomous AI Software Engineer

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " Starting Autonomous AI Software Engineer Engine " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# 1. Start PostgreSQL + pgvector Docker container
Write-Host "[1/3] Starting PostgreSQL + pgvector container..." -ForegroundColor Yellow
docker compose up -d postgres

# 2. Wait for DB to be healthy
Start-Sleep -Seconds 3

# 3. Launch Backend in a new terminal
Write-Host "[2/3] Launching FastAPI Backend on http://localhost:8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; python -m uvicorn app.main:app --reload --port 8000"

# 4. Launch Frontend in a new terminal
Write-Host "[3/3] Launching Frontend Dashboard on http://localhost:3000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"

Write-Host ""
Write-Host "All systems launched successfully!" -ForegroundColor Green
Write-Host "Dashboard: http://localhost:3000" -ForegroundColor White
Write-Host "API Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "=================================================" -ForegroundColor Cyan
