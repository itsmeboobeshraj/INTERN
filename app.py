import re

from flask import Flask, jsonify, request

from chatbot import ChatError, ConversationStore

app = Flask(__name__, static_folder="static", static_url_path="")
store = ConversationStore()

MAX_MESSAGE_CHARS = 2000
ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def _error(message, status):
    return jsonify({"error": message}), status


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True})


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    conversation_id = str(data.get("conversation_id", ""))
    message = str(data.get("message", "")).strip()

    if not ID_PATTERN.match(conversation_id):
        return _error("Missing or invalid conversation_id.", 400)
    if not message:
        return _error("Message can't be empty.", 400)
    if len(message) > MAX_MESSAGE_CHARS:
        return _error(f"Message is too long (max {MAX_MESSAGE_CHARS} characters).", 400)

    convo = store.get(conversation_id)
    try:
        reply = convo.send(message)
    except ChatError as e:
        return _error(e.message, e.status)
    except Exception:
        app.logger.exception("Unexpected error")
        return _error("Something went wrong on the server. Please try again.", 500)

    return jsonify({
        "reply": reply,
        "context": {"messages_in_window": len(convo.history), "has_summary": bool(convo.summary)},
    })


@app.post("/api/reset")
def reset():
    data = request.get_json(silent=True) or {}
    store.delete(str(data.get("conversation_id", "")))
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
