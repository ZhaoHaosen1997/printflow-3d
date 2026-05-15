@echo off
chcp 65001 >nul
echo ============================================
echo   PrintFlow-3D 一键启动
echo ============================================
echo.
echo 正在启动后端 (port 8848) ...
start "PrintFlow Backend" "%~dp0\start_backend.bat"

echo 正在启动前端 (port 5173) ...
start "PrintFlow Frontend" "%~dp0\start_frontend.bat"

echo.
echo ============================================
echo   启动完成！
echo   后端: http://localhost:8848
echo   API文档: http://localhost:8848/docs
echo   前端: http://localhost:5173
echo ============================================
echo.
echo 关闭本窗口不影响服务运行。
echo 如需停止服务，请运行 stop.bat
echo.

pause
