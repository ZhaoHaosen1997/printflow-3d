@echo off
setlocal enabledelayedexpansion
title PrintFlow-3D Stop

echo ============================================
echo   PrintFlow-3D Stop Services
echo ============================================
echo.

set killed=0

echo [1/2] Stopping Backend (port 8848) ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8848" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    if !errorlevel!==0 (
        echo   Stopped PID %%a
        set /a killed+=1
    )
)

echo [2/2] Stopping Frontend (port 5173) ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    if !errorlevel!==0 (
        echo   Stopped PID %%a
        set /a killed+=1
    )
)

echo.
if !killed!==0 (
    echo No running services found.
) else (
    echo Stopped !killed! service(s).
)
echo.

pause
