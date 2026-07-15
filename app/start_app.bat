@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Create it with: python -m venv .venv
    exit /b 1
)
set FLASK_SECRET_KEY=dev_secret_key
set FLASK_DEBUG=true
".venv\Scripts\python.exe" app.py
