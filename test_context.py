import chatbot
from chatbot import ChatError, Conversation


class FakeLLM:
    def __init__(self):
        self.calls = []
        self.fail_next = False

    def __call__(self, messages, system, max_tokens=800):
        self.calls.append({"messages": [dict(m) for m in messages], "system": system})
        if self.fail_next:
            self.fail_next = False
            raise ChatError("boom", 504)
        if "Update the running summary" in messages[-1]["text"]:
            return "SUMMARY: learner is Sam"
        return f"reply {len(self.calls)}"


def test_history_is_sent_each_turn():
    llm = FakeLLM()
    c = Conversation(llm)
    c.send("my name is Sam")
    c.send("what's a list?")
    c.send("what's my name?")
    assert [m["text"] for m in llm.calls[-1]["messages"]][0] == "my name is Sam"
    assert len(llm.calls[-1]["messages"]) == 5


def test_old_messages_are_summarised_and_window_stays_bounded():
    llm = FakeLLM()
    c = Conversation(llm)
    for i in range(10):
        c.send(f"msg {i}")
    assert len(c.history) <= chatbot.MAX_MESSAGES
    assert c.history[0]["role"] == "user"
    assert c.summary.startswith("SUMMARY")
    assert "SUMMARY: learner is Sam" in llm.calls[-1]["system"]


def test_failed_call_does_not_corrupt_history():
    llm = FakeLLM()
    c = Conversation(llm)
    c.send("hi")
    llm.fail_next = True
    try:
        c.send("this fails")
        assert False, "expected ChatError"
    except ChatError:
        pass
    assert [m["role"] for m in c.history] == ["user", "model"]
    c.send("retry")
    assert [m["role"] for m in c.history] == ["user", "model", "user", "model"]


def test_summary_failure_falls_back_to_truncation():
    llm = FakeLLM()
    c = Conversation(llm)
    for i in range(5):
        c.send(f"msg {i}")
    original = llm.__call__

    def flaky(messages, system, max_tokens=800):
        if "Update the running summary" in messages[-1]["text"]:
            raise ChatError("summary down", 503)
        return original(messages, system, max_tokens)

    c.llm = flaky
    c.send("msg 5")
    assert len(c.history) <= chatbot.MAX_MESSAGES


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
