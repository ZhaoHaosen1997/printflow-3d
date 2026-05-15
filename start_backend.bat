@echo off
chcp 65001 >nul
title PrintFlow-3D 后端

echo ============================================
echo   PrintFlow-3D 后端服务
echo   FastAPI ^| port 8848
echo ============================================
echo.

cd /d "%~dp0"

call backend\.venv\Scripts\activate.bat
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8848

pause
