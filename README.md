# Onity Mortgage AI Chatbot

A Python chatbot for Onity Mortgage chat support, grounded in the real onitymortgage.com/buy-a-home knowledge base (Purchase Promise programs, contact channels, the 6-step homebuying process). Free-form questions are answered by a real LLM — Anthropic Claude, Google Gemini, or OpenAI GPT — via genuine tool-calling: the model decides on its own when to run the payment calculator, promotion lookup, pre-qualification check, document checklist, rates pointer, homebuying steps, or human handoff.

Anything unrelated to Onity home loans gets a fixed deflection message instead of a guess (strict on-topic guardrail), and **every input and response is written to a log file** you can review at any time.

## Python files

| File | Purpose |
|---|---|
| `main.py` | Terminal chat interface — run this to talk to the bot |
| `app.py` | Web chat interface (Flask) — `python app.py`, then open http://localhost:5001 |
| `chatbot.py` | Core engine: the LLM tool-calling agent loop for all 3 providers |
| `knowledge_base.py` | The Onity RAG knowledge base + the AI behaviour instructions (system prompt, guardrail) |
| `tools.py` | The 7 tools the model can call (calculator, promos, prequal, checklist, rates, steps, handoff) |
| `chat_logger.py` | Conversation logging — writes every input/tool call/response to the log file |
| `config.py` | Provider/model/API-key/log settings |

## Setup

```bash
pip install -r requirements.txt
```

Pick a provider and set its API key (all three work — calls run server-side in Python, so even OpenAI's browser-CORS restriction doesn't apply here):

```bash
export PROVIDER=anthropic            # default; or: gemini / openai
export ANTHROPIC_API_KEY=sk-ant-...  # from console.anthropic.com/settings/keys
# or: export GEMINI_API_KEY=AIza...  # from aistudio.google.com/apikey
# or: export OPENAI_API_KEY=sk-...   # from platform.openai.com/api-keys
```

## Run

**Terminal chat:**

```bash
python main.py
```

```
You: What is the 1% Rate Drop?
  [tool used: get_promotion_details]
Bot: The 1% Rate Drop is a lender-paid temporary buydown on purchase loans...
```

**Web chat:**

```bash
python app.py     # then open http://localhost:5001
```

## Chat log

Every session appends to `logs/chat_log.txt` — session start, each user input, each tool call with its arguments and result, each assistant response, and any errors, all timestamped:

```
[2026-07-19 10:25:23] [session 3778a7c1] SESSION START: provider=anthropic model=claude-opus-4-8
[2026-07-19 10:25:23] [session 3778a7c1] USER: What is the 1% Rate Drop?
[2026-07-19 10:25:23] [session 3778a7c1] TOOL: get_promotion_details({'promotion': 'rate_drop_1pct'}) -> 1% Rate Drop: Type — Lender-paid 1/0 temporary buydown; ...
[2026-07-19 10:25:23] [session 3778a7c1] ASSISTANT: The 1% Rate Drop is a lender-paid buydown that lowers your payment for the first 12 months...
```

The `logs/` folder is created automatically on first run (and is gitignored so real customer conversations never get pushed to the repo). Change the location with `CHAT_LOG_DIR`.

## How the RAG grounding works

The knowledge base corpus in `knowledge_base.py` is injected into every request's system prompt (rather than retrieved conditionally), so grounding never drops mid-conversation — the corpus is small enough that inlining it beats a vector-retrieval pipeline. The system prompt also enforces: never quote live rates (the rates tool points to the real rates page instead), promotion figures must come from the `get_promotion_details` tool rather than model memory, hardship language triggers an immediate human handoff, and off-topic questions get a fixed deflection message.

## Also in this repo: browser-only HTML variants

- `index.html` — a generic, unbranded single-file chat widget template (bring-your-own-key, no backend). Fork it for any lender.
- `onity-assistant.html` — the Onity-branded single-file variant of the same widget.

These run entirely in the browser with the visitor's own API key and are deployable as static pages (e.g. Vercel/GitHub Pages). Note: unlike the Python app, the static pages cannot call OpenAI (its API blocks browser CORS requests) and cannot write a server-side log file — that's exactly what the Python version adds.

## Notes

- This is an independent prototype, not the official onitymortgage.com chat widget.
- Model defaults: `claude-opus-4-8`, `gemini-3.5-flash`, `gpt-5.4` — override with `ANTHROPIC_MODEL` / `GEMINI_MODEL` / `OPENAI_MODEL`.
- Informational only, not financial advice; loans subject to credit approval. Onity is not licensed in Hawaii.
