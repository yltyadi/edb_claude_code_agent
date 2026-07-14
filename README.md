---
title: EDB Macro Agent
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: "5.4.0"
python_version: "3.11"
app_file: app.py
pinned: false
---

# EDB Macro Intelligence Agent

Daily macro-intelligence brief pipeline for Emirates Development Bank, covering the five
Operation 300bn priority sectors.

## Production deployment — GitHub Actions + GitHub Pages

The live pipeline runs entirely on GitHub (free), no hosted server required:

- **Generation:** `.github/workflows/generate_brief.yml` runs the **Claude Agent SDK**
  runner (`run_agent_sdk.py`) on a **daily schedule**, on manual dispatch, and when a
  collaborator opens a *"Generate Brief"* issue (the GitHub Pages button). The runner
  produces the brief with real Bash code execution for the calculations.
- **Evaluation:** the same workflow then runs the **AutoRubric** evaluation automatically
  and commits the report alongside the brief.
- **Viewer:** the GitHub Pages site (`docs/index.html`) renders the latest brief and the
  latest AutoRubric score comparison, reading committed files from `outputs/`.

The workflow installs Node + the `claude` CLI (`npm i -g @anthropic-ai/claude-code`, which
the SDK drives) and routes the model through OpenRouter, so it reuses the existing
`OPENROUTER_API_KEY` — no Anthropic billing. Built-in WebSearch is an Anthropic server-side
tool that does not work through OpenRouter, so the agent searches via
`python3 run_tools.py search "<query>"` (DuckDuckGo) instead.

**Required repo secrets** (Settings → Secrets and variables → Actions): `OPENROUTER_API_KEY`,
`FRED_API_KEY`. Optional repo *variables*: `OPENROUTER_MODEL` (default
`anthropic/claude-sonnet-4-6`), `AGENT_MAX_BUDGET_USD`, `AUTORUBRIC_JUDGES`.

## Optional: Hugging Face Gradio Space (interactive viewer)

`app.py` is a Gradio UI for browsing briefs, running evals, and chatting about a brief. On
the free HF Gradio tier it runs the legacy `run_agent.py` (no Node/CLI available there); the
Agent SDK path (`USE_AGENT_SDK=1`, `run_agent_sdk.py`) requires Node + the `claude` CLI and
therefore a Docker-capable host (the included `Dockerfile` targets that — e.g. Cloud Run).

## Local run

```bash
pip install -r requirements.txt              # incl. claude-agent-sdk
npm install -g @anthropic-ai/claude-code     # the CLI the SDK drives
python run_agent_sdk.py                      # generate one brief locally (uses the SDK)
python -m eval_autorubric.run_eval           # score the latest briefs
```
