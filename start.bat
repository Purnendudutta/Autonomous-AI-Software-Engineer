@echo off
title Autonomous AI Software Engineer Launcher
echo ===================================================
echo   Autonomous AI Software Engineer Launcher
echo ===================================================
echo.

:: 1. Start Docker container for database
echo [1/3] Starting Database container (aie_postgres)...
docker start aie_postgres >nul 2>&1
timeout /t 2 /nobreak >nul

:: 2. Launch Backend in a new window
echo [2/3] Launching Backend Server on port 8000...
start "AI Engineer - Backend (Port 8000)" cmd /k "cd /d D:\Autonomous-AI-Software-Engineer\backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait for backend to initialize
timeout /t 3 /nobreak >nul

:: 3. Launch Frontend in a new window
echo [3/3] Launching Frontend Server on port 3000...
start "AI Engineer - Frontend (Port 3000)" cmd /k "cd /d D:\Autonomous-AI-Software-Engineer\frontend && npm run dev"

echo.
echo ===================================================
echo   All services launched!
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo ===================================================
echo Opening your browser in 3 seconds...
timeout /t 3 /nobreak >nul
start http://localhost:3000
