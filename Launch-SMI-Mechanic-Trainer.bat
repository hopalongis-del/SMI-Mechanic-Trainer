@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
)
set PYTHON=.venv\Scripts\python.exe
"%PYTHON%" -m pip install -q --upgrade pip
"%PYTHON%" -m pip install -q -r requirements.txt
"%PYTHON%" test_smoke.py
if errorlevel 1 (
    echo Tests failed.
    exit /b 1
)
start "" "http://127.0.0.1:8060/"
"%PYTHON%" -m uvicorn server:app --host 127.0.0.1 --port 8060
