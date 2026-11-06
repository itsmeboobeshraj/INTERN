from chatbot import ChatError, Conversation

convo = Conversation()
print("Pip, your Python tutor. Type /reset to start over, /quit to exit.\n")
while True:
    try:
        text = input("you > ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if text == "/quit":
        break
    if text == "/reset":
        convo.reset()
        print("(conversation cleared)\n")
        continue
    if not text:
        continue
    try:
        print(f"\npip > {convo.send(text)}\n")
    except ChatError as e:
        print(f"\n[error] {e.message}\n")
