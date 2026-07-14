@echo off
chcp 65001 >nul
setlocal

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo .venv를 찾을 수 없습니다. install_windows.bat을 먼저 실행하세요.
    exit /b 1
)

"%~dp0.venv\Scripts\python.exe" "%~dp0app.py"
