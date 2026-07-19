"""Terminal chat interface for the Onity Mortgage assistant.

Run:
    export ANTHROPIC_API_KEY=sk-ant-...      # or GEMINI_API_KEY / OPENAI_API_KEY
    export PROVIDER=anthropic                # or gemini / openai (default: anthropic)
    python main.py

Type your question and press Enter; type 'quit' or 'exit' (or Ctrl-C) to
leave. The full conversation — inputs, tool calls, and responses — is
appended to logs/chat_log.txt.
"""

import config
from chatbot import ChatbotError, OnityChatbot


def run() -> None:
    config.validate()
    bot = OnityChatbot()
    print("=" * 60)
    print("Onity Mortgage Assistant")
    print(f"Provider: {bot.provider}  Model: {bot.model}")
    print(f"Log file: {config.LOG_FILE}")
    print("Type 'quit' to exit.")
    print("=" * 60)
    print("\nBot: Hi! I'm the Onity Mortgage assistant. Ask me about buying a "
          "home, our Purchase Promise programs, or your account.\n")

    while True:
        try:
            user_text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBot: Goodbye!")
            break
        if not user_text:
            continue
        if user_text.lower() in ("quit", "exit", "bye"):
            print("Bot: Goodbye!")
            break
        try:
            reply = bot.send(user_text)
        except ChatbotError as exc:
            print(f"\n[error] {exc}\n")
            continue
        for tool_name in bot.tools_used:
            print(f"  [tool used: {tool_name}]")
        print(f"\nBot: {reply}\n")


if __name__ == "__main__":
    run()
