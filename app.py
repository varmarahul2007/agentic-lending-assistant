"""Web chat interface for the Onity Mortgage assistant (Flask).

Run:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...      # or GEMINI_API_KEY / OPENAI_API_KEY
    export PROVIDER=anthropic                # or gemini / openai
    python app.py

Then open http://localhost:5001 — a simple chat page backed by
POST /chat. (Port 5001 by default because macOS AirPlay occupies 5000;
override with the PORT environment variable.) Because all LLM calls happen server-side in Python, every
provider works here, including OpenAI (which blocks direct browser
calls). All inputs, tool calls, and responses go to logs/chat_log.txt.
"""

import os

from flask import Flask, jsonify, render_template_string, request, session

import config
from chatbot import ChatbotError, OnityChatbot

app = Flask(__name__)
app.secret_key = "onity-demo-not-for-production"

# One chatbot (with its own history + log session) per browser session.
_bots = {}


def _get_bot() -> OnityChatbot:
    sid = session.get("sid")
    if sid is None or sid not in _bots:
        bot = OnityChatbot()
        session["sid"] = bot.session_id
        _bots[bot.session_id] = bot
        return bot
    return _bots[sid]


PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Onity Mortgage Assistant</title>
<style>
  body{font-family:system-ui,sans-serif;background:#F5F6FB;margin:0;display:flex;justify-content:center;}
  .chat{width:min(640px,95vw);margin:24px 0;background:#fff;border:1px solid #DFE1F0;border-radius:16px;
        display:flex;flex-direction:column;height:calc(100vh - 48px);}
  header{padding:14px 18px;border-bottom:1px solid #DFE1F0;font-weight:700;}
  header small{display:block;font-weight:400;color:#52546E;}
  #log{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;}
  .msg{max-width:85%;padding:9px 13px;border-radius:12px;font-size:14px;line-height:1.5;white-space:pre-wrap;}
  .user{align-self:flex-end;background:#3226E3;color:#fff;}
  .bot{align-self:flex-start;background:#EDEBFE;color:#14152B;}
  .tool{align-self:flex-start;font-size:12px;color:#3226E3;font-weight:600;}
  .err{align-self:flex-start;background:#FBEAE8;color:#C4433A;}
  form{display:flex;gap:8px;padding:12px;border-top:1px solid #DFE1F0;}
  input{flex:1;border:1px solid #DFE1F0;border-radius:999px;padding:10px 15px;font-size:14px;}
  button{border:none;background:#3226E3;color:#fff;border-radius:999px;padding:0 20px;font-weight:700;cursor:pointer;}
</style>
</head>
<body>
<div class="chat">
  <header>Onity Mortgage Assistant
    <small>Provider: {{ provider }} &middot; Model: {{ model }} &middot; log: logs/chat_log.txt</small>
  </header>
  <div id="log"><div class="msg bot">Hi! I'm the Onity Mortgage assistant. Ask me about buying a home, our Purchase Promise programs, or your account.</div></div>
  <form id="f"><input id="t" autocomplete="off" placeholder="Ask about buying, promos, or your account..."><button>Send</button></form>
</div>
<script>
const log=document.getElementById('log'),form=document.getElementById('f'),input=document.getElementById('t');
function add(cls,text){const d=document.createElement('div');d.className='msg '+cls;d.textContent=text;log.appendChild(d);log.scrollTop=log.scrollHeight;return d;}
form.addEventListener('submit',async e=>{
  e.preventDefault();
  const text=input.value.trim(); if(!text)return;
  input.value=''; add('user',text);
  const typing=add('bot','...');
  try{
    const r=await fetch('/chat',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({message:text})});
    const data=await r.json();
    typing.remove();
    (data.tools_used||[]).forEach(t=>add('tool','[tool used: '+t+']'));
    if(data.error) add('err',data.error); else add('bot',data.reply);
  }catch(err){ typing.remove(); add('err','Request failed: '+err); }
});
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(PAGE, provider=config.PROVIDER, model=config.MODELS[config.PROVIDER])


@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400
    bot = _get_bot()
    try:
        reply = bot.send(message)
    except ChatbotError as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify({"reply": reply, "tools_used": bot.tools_used})


if __name__ == "__main__":
    config.validate()
    port = int(os.environ.get("PORT", 5001))
    print(f"Onity chatbot running — open http://localhost:{port}")
    print(f"Conversation log: {config.LOG_FILE}")
    app.run(host="127.0.0.1", port=port, debug=False)
