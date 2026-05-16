@echo off
setlocal enabledelayedexpansion
title PrintFlow-3D Backend

echo ============================================
echo   PrintFlow-3D Backend
echo   FastAPI ^| port 8848
echo ============================================
echo.

cd /d "%~dp0"
call backend\.venv\Scripts\activate.bat
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8848

pause
