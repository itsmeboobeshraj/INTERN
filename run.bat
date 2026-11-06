@echo off
cd /d "%~dp0"
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -q -r requirements.txt
if not exist .env (
  copy .env.example .env >nul
  echo Created .env. Add your GEMINI_API_KEY, then run run.bat again.
  exit /b 0
)
if "%1"=="cli" (python cli.py) else (python app.py)
