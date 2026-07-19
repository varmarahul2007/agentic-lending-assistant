"""Configuration for the Onity Mortgage chatbot.

Pick the LLM provider with the PROVIDER environment variable
("anthropic", "gemini", or "openai") and supply the matching API key:

    export PROVIDER=anthropic
    export ANTHROPIC_API_KEY=sk-ant-...

    export PROVIDER=gemini
    export GEMINI_API_KEY=AIza...

    export PROVIDER=openai
    export OPENAI_API_KEY=sk-...

All calls run server-side from Python, so every provider works here
(including OpenAI, which blocks direct browser calls).
"""

import os

# Which LLM answers the chat. One of: "anthropic", "gemini", "openai".
PROVIDER = os.environ.get("PROVIDER", "anthropic").strip().lower()

MODELS = {
    "anthropic": os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8"),
    "gemini": os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
    # Verify against platform.openai.com/docs/models — OpenAI's lineup moves fast.
    "openai": os.environ.get("OPENAI_MODEL", "gpt-5.4"),
}

API_KEY_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
}

# Where conversation logs are written. Every user input, tool call, and
# assistant response is appended here with a timestamp.
LOG_DIR = os.environ.get("CHAT_LOG_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"))
LOG_FILE = os.path.join(LOG_DIR, "chat_log.txt")

# Safety valve for the tool-calling loop.
MAX_TOOL_ITERATIONS = 6

# Max tokens for each model response (Anthropic requires this explicitly).
MAX_TOKENS = 1200


def get_api_key(provider: str = None) -> str:
    """Return the API key for the given (or configured) provider, or ''."""
    provider = provider or PROVIDER
    env_var = API_KEY_ENV_VARS.get(provider, "")
    return os.environ.get(env_var, "").strip()


def validate() -> None:
    """Fail fast with a clear message if the configuration is unusable."""
    if PROVIDER not in MODELS:
        raise SystemExit(
            f"Unknown PROVIDER '{PROVIDER}'. Use one of: {', '.join(MODELS)}"
        )
    if not get_api_key():
        raise SystemExit(
            f"No API key found. Set {API_KEY_ENV_VARS[PROVIDER]} in your "
            f"environment (current provider: {PROVIDER})."
        )
