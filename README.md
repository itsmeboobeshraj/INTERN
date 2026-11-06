# Pip

Multi-turn Gemini chatbot with a Flask backend, browser UI and CLI.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

`python cli.py` runs the terminal version. `python test_context.py` runs the tests.

## Files

- `chatbot.py`: Gemini call, error mapping, per-conversation history, summarisation
- `app.py`: `POST /api/chat`, `POST /api/reset`, `GET /api/health`
- `static/index.html`: chat UI
- `cli.py`: terminal chat
- `test_context.py`: tests using a fake model

## Context management

When history exceeds `MAX_MESSAGES`, older messages are summarised into a running summary and only the last `KEEP_MESSAGES` are kept verbatim. If summarising fails, old messages are dropped.

## Config (.env)

`GEMINI_API_KEY`, `GEMINI_MODEL`, `MAX_MESSAGES`, `KEEP_MESSAGES`, `REQUEST_TIMEOUT_SECONDS`
