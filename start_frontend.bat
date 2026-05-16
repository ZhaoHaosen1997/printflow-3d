@echo off
setlocal enabledelayedexpansion
title PrintFlow-3D Frontend

echo ============================================
echo   PrintFlow-3D Frontend
echo   Vite ^| port 5173
echo ============================================
echo.

cd /d "%~dp0frontend"
npx vite --host

pause
