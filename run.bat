@echo off
setlocal
cd /d "%~dp0"

echo [ProposalForge] Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo pip install failed.
  exit /b 1
)

if not exist "data" mkdir data
if not exist "samples" mkdir samples
if not exist "..\..\ops" mkdir "..\..\ops"

echo [ProposalForge] Starting server on http://127.0.0.1:8787
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
