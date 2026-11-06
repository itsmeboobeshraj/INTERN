import os
import threading
from collections import OrderedDict

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "12"))
KEEP_MESSAGES = int(os.getenv("KEEP_MESSAGES", "6"))
TIMEOUT_MS = int(float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")) * 1000)
MAX_CONVERSATIONS = 500

SYSTEM_PROMPT = """You are Pip, a patient Python tutor for beginners.

Role and style:
- Explain concepts in plain language, then show a short code example.
- Keep answers under about 200 words unless the learner asks for more.
- When the learner shares broken code, point to the bug first, then explain why it happens.
- Ask at most one follow-up question per reply, to check understanding.

Boundaries:
- Stay on programming and learning-to-code topics. If asked about something else,
  say so in one sentence and steer back to coding.
- If you are not sure about something, say so instead of guessing.
- Refer back to earlier parts of the conversation when it helps the learner."""


class ChatError(Exception):

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.message = message
        self.status = status


_client = None


def _get_client():
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise ChatError(
                "The server has no GEMINI_API_KEY configured. Add it to your .env file.", 500
            )
        _client = genai.Client(
            api_key=key, http_options=types.HttpOptions(timeout=TIMEOUT_MS)
        )
    return _client


def call_llm(messages, system_instruction, max_tokens=800):
    client = _get_client()
    contents = [
        types.Content(role=m["role"], parts=[types.Part(text=m["text"])]) for m in messages
    ]
    try:
        resp = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=max_tokens,
                temperature=0.7,
            ),
        )
    except errors.APIError as e:
        code = getattr(e, "code", None)
        if code == 429:
            raise ChatError("Too many requests right now. Wait a few seconds and try again.", 429)
        if code in (401, 403):
            raise ChatError("The API key was rejected. Check GEMINI_API_KEY on the server.", 500)
        if code == 400:
            raise ChatError("The AI service rejected that request. Try rephrasing.", 400)
        if code and code >= 500:
            raise ChatError("The AI service is having problems. Try again in a moment.", 503)
        raise ChatError("The AI service returned an error. Please try again.", 502)
    except Exception:
        raise ChatError(
            "Couldn't reach the AI service (network problem or timeout). Please try again.", 504
        )

    text = (resp.text or "").strip()
    if not text:
        raise ChatError(
            "The model returned no text, possibly because a safety filter blocked it. "
            "Try rephrasing your message.",
            502,
        )
    return text


class Conversation:

    def __init__(self, llm=call_llm):
        self.history = []
        self.summary = ""
        self.llm = llm
        self.lock = threading.Lock()

    def _system_instruction(self):
        if not self.summary:
            return SYSTEM_PROMPT
        return (
            SYSTEM_PROMPT
            + "\n\nSummary of the earlier part of this conversation "
            "(those messages are no longer shown):\n" + self.summary
        )

    def send(self, user_text: str) -> str:
        with self.lock:
            self.history.append({"role": "user", "text": user_text})
            try:
                reply = self.llm(self.history, self._system_instruction())
            except ChatError:
                self.history.pop()
                raise
            self.history.append({"role": "model", "text": reply})
            self._compact()
            return reply

    def _compact(self):
        if len(self.history) <= MAX_MESSAGES:
            return
        cut = len(self.history) - KEEP_MESSAGES
        old, self.history = self.history[:cut], self.history[cut:]
        while self.history and self.history[0]["role"] != "user":
            self.history.pop(0)

        transcript = "\n".join(
            f"{'Learner' if m['role'] == 'user' else 'Pip'}: {m['text']}" for m in old
        )
        prompt = (
            "Update the running summary of a tutoring conversation.\n\n"
            f"Existing summary:\n{self.summary or '(none yet)'}\n\n"
            f"New messages to fold in:\n{transcript}\n\n"
            "Write the updated summary in under 150 words. Keep the learner's name, goals, "
            "skill level, topics covered, and any unresolved questions. Output only the summary."
        )
        try:
            self.summary = self.llm([{"role": "user", "text": prompt}],
                                    "You write concise, factual summaries.", 300).strip()
        except ChatError:
            pass

    def reset(self):
        with self.lock:
            self.history, self.summary = [], ""


class ConversationStore:

    def __init__(self, llm=call_llm):
        self._llm = llm
        self._items = OrderedDict()
        self._lock = threading.Lock()

    def get(self, conversation_id: str) -> Conversation:
        with self._lock:
            if conversation_id not in self._items:
                self._items[conversation_id] = Conversation(self._llm)
                while len(self._items) > MAX_CONVERSATIONS:
                    self._items.popitem(last=False)
            self._items.move_to_end(conversation_id)
            return self._items[conversation_id]

    def delete(self, conversation_id: str):
        with self._lock:
            self._items.pop(conversation_id, None)
