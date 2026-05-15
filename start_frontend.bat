@echo off
chcp 65001 >nul
title PrintFlow-3D 前端

echo ============================================
echo   PrintFlow-3D 前端服务
echo   Vite ^| port 5173
echo ============================================
echo.

cd /d "%~dp0\frontend"

call npx vite --host

pause
