@echo off
chcp 65001 >nul
title PrintFlow-3D 停止服务

echo ============================================
echo   PrintFlow-3D 停止服务
echo ============================================
echo.

set killed=0

echo [1/2] 停止后端 (port 8848) ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8848" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    if not errorlevel 1 (
        echo   已停止 PID %%a
        set /a killed+=1
    )
)

echo [2/2] 停止前端 (port 5173) ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    if not errorlevel 1 (
        echo   已停止 PID %%a
        set /a killed+=1
    )
)

echo.
if %killed%==0 (
    echo 未发现正在运行的服务。
) else (
    echo 已停止 %killed% 个服务。
)
echo.

pause
