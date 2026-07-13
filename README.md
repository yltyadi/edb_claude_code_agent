---
title: EDB Macro Agent
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# EDB Macro Intelligence Agent

Daily macro-intelligence brief pipeline for Emirates Development Bank, deployed as a
Hugging Face **Docker** Space (Gradio UI on port 7860).

## Brief generation runners

Two interchangeable runners write to `outputs/` and emit the same `SUMMARY_JSON` contract:

| Runner | How it works | Selected when |
|--------|--------------|---------------|
| `run_agent.py` (legacy) | Hand-rolled OpenRouter tool-calling loop; no code execution | default |
| `run_agent_sdk.py` | **Claude Agent SDK** (Claude Code engine) routed to OpenRouter; real Bash code execution for calculations, WebFetch, file tools | `USE_AGENT_SDK=1` |

The SDK runner reuses the OpenRouter key (no Anthropic billing). Built-in WebSearch is an
Anthropic server-side tool and does not work through OpenRouter, so the agent searches via
`python3 run_tools.py search "<query>"` (DuckDuckGo) instead. The `claude` CLI (Node,
installed in the Dockerfile via `npm i -g @anthropic-ai/claude-code`) is required by the SDK.

## Required Space secrets / variables

| Name | Purpose |
|------|---------|
| `OPENROUTER_API_KEY` | Model inference (both runners) |
| `FRED_API_KEY` | FRED economic series |
| `GITHUB_TOKEN`, `GITHUB_REPO` | Commit briefs/evals back to the repo |
| `USE_AGENT_SDK` | Set to `1` to use the Agent SDK runner |
| `OPENROUTER_MODEL` | Optional; default `anthropic/claude-sonnet-4-6` (use a Claude model) |
| `AGENT_MAX_TURNS`, `AGENT_MAX_BUDGET_USD` | Optional safety caps for the SDK runner |

`ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` are set automatically by `run_agent_sdk.py`
from `OPENROUTER_API_KEY`; do not set `ANTHROPIC_API_KEY` (it would override the routing).

## Local run

```bash
pip install -r requirements.txt              # incl. claude-agent-sdk
npm install -g @anthropic-ai/claude-code     # the CLI the SDK drives
USE_AGENT_SDK=1 python run_agent_sdk.py      # generate one brief locally
```
