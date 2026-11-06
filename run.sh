#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env. Add your GEMINI_API_KEY, then run ./run.sh again."
  exit 0
fi
if [ "$1" = "cli" ]; then python cli.py; else python app.py; fi
