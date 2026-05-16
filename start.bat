@echo off
setlocal enabledelayedexpansion
title PrintFlow-3D Start

echo ============================================
echo   PrintFlow-3D Start All Services
echo ============================================
echo.

echo [1/2] Starting Backend (port 8848) ...
start "PrintFlow-Backend" cmd /c "cd /d %~dp0 && backend\.venv\Scripts\activate.bat && python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8848"

echo [2/2] Starting Frontend (port 5173) ...
start "PrintFlow-Frontend" cmd /c "cd /d %~dp0frontend && npx vite --host"

echo.
echo ============================================
echo   All services started!
echo.
echo   Backend : http://localhost:8848
echo   API Docs: http://localhost:8848/docs
echo   Frontend: http://localhost:5173
echo ============================================
echo.
echo Close this window to stop all services,
echo or run stop.bat
echo.

pause
