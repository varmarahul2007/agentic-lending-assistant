"""Core chatbot engine: a genuine LLM tool-calling agent loop.

The conversation history is stored provider-agnostically as
[{"role": "user"|"assistant", "text": ...}] and translated to each
provider's wire format fresh on every call, so the provider can even be
switched mid-conversation. Supported providers: Anthropic (Claude),
Google (Gemini), OpenAI (GPT), and DeepSeek — all called server-side
via requests. DeepSeek's API is OpenAI-compatible, so it shares the
OpenAI code path with a different base URL.

Usage:
    bot = OnityChatbot()
    reply = bot.send("What is the 1% Rate Drop?")
"""

import json

import requests

import chat_logger
import config
from knowledge_base import SYSTEM_PROMPT
from tools import TOOL_SCHEMAS, execute_tool


class ChatbotError(RuntimeError):
    """Raised when the LLM API call fails; message is safe to show users."""


class OnityChatbot:
    def __init__(self, provider: str = None, session_id: str = None):
        self.provider = (provider or config.PROVIDER).lower()
        if self.provider not in config.MODELS:
            raise ChatbotError(f"Unknown provider '{self.provider}'")
        self.model = config.MODELS[self.provider]
        self.session_id = session_id or chat_logger.new_session_id()
        self.history = []  # [{"role": "user"|"assistant", "text": str}]
        self.tools_used = []  # tool names called while answering the last message
        chat_logger.log_session_start(self.session_id, self.provider, self.model)

    # ------------------------------------------------------------------
    def send(self, user_text: str) -> str:
        """Send one user message; returns the assistant's reply text."""
        user_text = user_text.strip()
        if not user_text:
            return ""
        chat_logger.log_user(self.session_id, user_text)
        self.history.append({"role": "user", "text": user_text})
        self.tools_used = []
        try:
            if self.provider == "gemini":
                reply = self._run_gemini()
            elif self.provider == "openai":
                reply = self._run_openai_compatible("OpenAI", "https://api.openai.com/v1/chat/completions")
            elif self.provider == "deepseek":
                reply = self._run_openai_compatible("DeepSeek", "https://api.deepseek.com/chat/completions")
            else:
                reply = self._run_anthropic()
        except ChatbotError as exc:
            chat_logger.log_error(self.session_id, str(exc))
            raise
        except requests.RequestException as exc:
            msg = f"Could not reach the {self.provider} API: {exc}"
            chat_logger.log_error(self.session_id, msg)
            raise ChatbotError(msg) from exc
        self.history.append({"role": "assistant", "text": reply})
        chat_logger.log_assistant(self.session_id, reply)
        return reply

    def _record_tool(self, name: str, args: dict) -> str:
        result = execute_tool(name, args)
        self.tools_used.append(name)
        chat_logger.log_tool(self.session_id, name, args, result)
        return result

    def _api_key(self) -> str:
        key = config.get_api_key(self.provider)
        if not key:
            raise ChatbotError(
                f"No API key set. Export {config.API_KEY_ENV_VARS[self.provider]} "
                f"before starting the chatbot."
            )
        return key

    @staticmethod
    def _check_response(resp: requests.Response, provider: str) -> dict:
        if resp.status_code != 200:
            raise ChatbotError(f"{provider} API error {resp.status_code}: {resp.text[:500]}")
        return resp.json()

    # ------------------------------------------------------------------
    def _run_anthropic(self) -> str:
        messages = [
            {"role": m["role"], "content": [{"type": "text", "text": m["text"]}]}
            for m in self.history
        ]
        for _ in range(config.MAX_TOOL_ITERATIONS):
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "content-type": "application/json",
                    "x-api-key": self._api_key(),
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": self.model,
                    "max_tokens": config.MAX_TOKENS,
                    "system": SYSTEM_PROMPT,
                    "tools": TOOL_SCHEMAS,
                    "messages": messages,
                },
                timeout=120,
            )
            data = self._check_response(resp, "Anthropic")
            if data.get("stop_reason") == "tool_use":
                messages.append({"role": "assistant", "content": data["content"]})
                tool_results = []
                for block in data["content"]:
                    if block.get("type") == "tool_use":
                        result = self._record_tool(block["name"], block.get("input") or {})
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block["id"],
                            "content": result,
                        })
                messages.append({"role": "user", "content": tool_results})
                continue
            texts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
            return texts[0] if texts else ""
        raise ChatbotError("Too many tool iterations")

    # ------------------------------------------------------------------
    def _run_gemini(self) -> str:
        contents = [
            {"role": "model" if m["role"] == "assistant" else "user",
             "parts": [{"text": m["text"]}]}
            for m in self.history
        ]
        gemini_tools = [{
            "functionDeclarations": [
                {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}
                for t in TOOL_SCHEMAS
            ]
        }]
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.model}:generateContent?key={self._api_key()}")
        for _ in range(config.MAX_TOOL_ITERATIONS):
            resp = requests.post(
                url,
                headers={"content-type": "application/json"},
                json={
                    "contents": contents,
                    "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                    "tools": gemini_tools,
                },
                timeout=120,
            )
            data = self._check_response(resp, "Gemini")
            candidates = data.get("candidates") or [{}]
            parts = (candidates[0].get("content") or {}).get("parts") or []
            function_calls = [p["functionCall"] for p in parts if "functionCall" in p]
            if function_calls:
                contents.append({"role": "model", "parts": parts})
                response_parts = []
                for fc in function_calls:
                    result = self._record_tool(fc["name"], fc.get("args") or {})
                    fr = {"name": fc["name"], "response": {"result": result}}
                    if fc.get("id"):
                        fr["id"] = fc["id"]
                    response_parts.append({"functionResponse": fr})
                contents.append({"role": "user", "parts": response_parts})
                continue
            texts = [p["text"] for p in parts if isinstance(p.get("text"), str)]
            return texts[0] if texts else ""
        raise ChatbotError("Too many tool iterations")

    # ------------------------------------------------------------------
    def _run_openai_compatible(self, provider_label: str, endpoint: str) -> str:
        """Agent loop for OpenAI-format chat-completions APIs (OpenAI, DeepSeek)."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += [{"role": m["role"], "content": m["text"]} for m in self.history]
        openai_tools = [
            {"type": "function",
             "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
            for t in TOOL_SCHEMAS
        ]
        for _ in range(config.MAX_TOOL_ITERATIONS):
            resp = requests.post(
                endpoint,
                headers={
                    "content-type": "application/json",
                    "Authorization": f"Bearer {self._api_key()}",
                },
                json={"model": self.model, "messages": messages, "tools": openai_tools},
                timeout=120,
            )
            data = self._check_response(resp, provider_label)
            msg = data["choices"][0]["message"]
            if msg.get("tool_calls"):
                messages.append(msg)
                for tc in msg["tool_calls"]:
                    try:
                        args = json.loads(tc["function"].get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = self._record_tool(tc["function"]["name"], args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })
                continue
            return msg.get("content") or ""
        raise ChatbotError("Too many tool iterations")
