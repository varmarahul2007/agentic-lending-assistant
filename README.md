# Agentic Lending Assistant

A single-file, Claude-powered chat widget template for a mortgage/lending site. Free-form questions are answered by the real Claude API — the model decides on its own when to run a payment calculator, a pre-qualification check, a document checklist, a rate lookup, or a human handoff, via genuine tool-calling. Also includes voice input/output via the Web Speech API.

It's one static `index.html` file with no build step and no backend.

## Two variants in this repo

- **`index.html`** — the generic, unbranded template described below. Fork it for any lender.
- **`onity-assistant.html`** — a real-content variant grounded in Onity Mortgage's published buy-a-home knowledge base (Purchase Promise programs, contact channels, the 6-step process), with an on-topic-only guardrail: anything unrelated to Onity home loans gets a fixed deflection message instead of a guess. Independent prototype, not the official onitymortgage.com widget.

## Try it

Open `index.html` in a browser (or visit the deployed URL), click the ⚙️ button, and paste an [Anthropic API key](https://console.anthropic.com/settings/keys). The key is stored only in your browser's `localStorage` and sent directly to `api.anthropic.com` — this repo has no server.

**Note:** this only works when the page is served as a normal site (opened locally, GitHub Pages, Vercel, etc.). It will *not* work inside an embedded preview/iframe sandbox (including Claude's own Artifact viewer) — those block outbound network requests, and the page will tell you so if it detects it's embedded.

## Customize it for your own lender

Everything lives in `index.html`. Open the `<script>` tag near the bottom and edit:

- `COMPANY_NAME` — swap out the "Northstar Home Loans" placeholder
- `SYSTEM_PROMPT` — the assistant's persona and behavior
- `TOOLS` — the JSON schemas Claude can call (payment calculator, pre-qualification, document checklist, rates, human handoff); each has a matching `tool...` implementation function to edit
- `MODEL_ID` — defaults to `claude-opus-4-8`; swap for a faster/cheaper model if you want

## Production note

Storing a real API key in every visitor's browser is fine for a demo or an internal tool, but not for a public consumer product — anyone can read it out of `localStorage`. For production, proxy requests through your own backend (or a small serverless function) so the key never reaches the client.

## Deploy

- **GitHub Pages**: enable Pages on this repo, serve from the root — `index.html` is already Pages-ready.
- **Vercel**: `vercel deploy` from this directory, or connect the repo in the Vercel dashboard. No build settings needed (static file).

## License

Add a license of your choice before publishing.
