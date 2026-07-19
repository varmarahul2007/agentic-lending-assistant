"""Conversation logging for the Onity chatbot.

Every user input, tool call, assistant response, and error is appended to
a single human-readable log file (logs/chat_log.txt by default) with a
timestamp and a session id, so a full transcript of what was asked and
what was answered can be reviewed at any time.
"""

import datetime
import os
import threading
import uuid

import config

_lock = threading.Lock()


def new_session_id() -> str:
    return uuid.uuid4().hex[:8]


def _write(session_id: str, kind: str, text: str) -> None:
    os.makedirs(config.LOG_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Keep multi-line messages readable but attributable to one entry.
    body = str(text).replace("\n", "\n" + " " * 4)
    line = f"[{timestamp}] [session {session_id}] {kind}: {body}\n"
    with _lock:
        with open(config.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)


def log_session_start(session_id: str, provider: str, model: str) -> None:
    _write(session_id, "SESSION START", f"provider={provider} model={model}")


def log_user(session_id: str, text: str) -> None:
    _write(session_id, "USER", text)


def log_tool(session_id: str, name: str, args: dict, result: str) -> None:
    _write(session_id, "TOOL", f"{name}({args}) -> {result}")


def log_assistant(session_id: str, text: str) -> None:
    _write(session_id, "ASSISTANT", text)


def log_error(session_id: str, message: str) -> None:
    _write(session_id, "ERROR", message)
