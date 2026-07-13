#!/usr/bin/env python3
"""
EDB Macro Intelligence Agent — Claude Agent SDK runner.

Replaces the hand-rolled OpenRouter tool-calling loop (run_agent.py) with the
Claude Agent SDK (the engine behind Claude Code). The SDK drives the same
Bash-native workflow that CLAUDE.md already documents — running the data tools
via `python3 run_tools.py ...`, executing the four required calculations as real
Python, and writing the brief + state.json with the file tools — which is what
made the interactive Claude Code briefs higher quality than the old loop.

Routing: the SDK's Anthropic client is pointed at OpenRouter's Anthropic-
compatible endpoint, so the existing OPENROUTER_API_KEY is reused (no Anthropic
billing). Built-in WebSearch is an Anthropic server-side tool and does NOT work
through OpenRouter, so it is excluded from allowed_tools; the agent searches via
`python3 run_tools.py search "<query>"` (DuckDuckGo) and WebFetch instead.

Usage:
  OPENROUTER_API_KEY=xxx FRED_API_KEY=xxx python run_agent_sdk.py
  OPENROUTER_MODEL=anthropic/claude-opus-4-8 python run_agent_sdk.py

Prints progress lines to stdout (streamed by app.py) and a final
`SUMMARY_JSON={...}` line matching run_agent.py's contract.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

# ── Route the SDK's Anthropic client to OpenRouter (before importing the SDK) ──
_OR_KEY = os.environ.get("OPENROUTER_API_KEY", "")
if _OR_KEY:
    os.environ.setdefault("ANTHROPIC_BASE_URL", "https://openrouter.ai/api")
    os.environ["ANTHROPIC_AUTH_TOKEN"] = _OR_KEY
    # A stray ANTHROPIC_API_KEY would override the OpenRouter auth token.
    os.environ.pop("ANTHROPIC_API_KEY", None)

from claude_agent_sdk import (  # noqa: E402
    query, ClaudeAgentOptions,
    AssistantMessage, ResultMessage, SystemMessage,
    TextBlock, ThinkingBlock, ToolUseBlock, ToolResultBlock,
)

STATE_PATH = ROOT / "outputs" / "state.json"
OUTPUTS_DIR = ROOT / "outputs"
COMMAND_PATH = ROOT / ".claude" / "commands" / "edb-brief.md"

MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-6")
MAX_TURNS = int(os.environ.get("AGENT_MAX_TURNS", "120"))
_BUDGET = os.environ.get("AGENT_MAX_BUDGET_USD")
MAX_BUDGET_USD = float(_BUDGET) if _BUDGET else None

# Local tools only — WebSearch is Anthropic server-side and unavailable via OpenRouter.
ALLOWED_TOOLS = ["Bash", "Read", "Write", "Edit", "Grep", "Glob", "WebFetch", "TodoWrite"]


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {"agent_version": "v2", "baselines": {}, "streaks": {}}


def build_prompt(state: dict) -> str:
    """Use the /edb-brief command doc as the task spec, with runtime context on top.

    CLAUDE.md is auto-loaded via setting_sources=["project"], so we don't repeat it.
    We override the one instruction that can't hold under OpenRouter routing:
    WebSearch is unavailable — the agent must search via run_tools.py search / WebFetch.
    """
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    last_run_date = state.get("last_run", {}).get("date", "N/A")
    agent_version = state.get("agent_version", "v2")
    command_body = COMMAND_PATH.read_text() if COMMAND_PATH.exists() else ""

    header = f"""Current UTC datetime: {now_utc}
Last run date: {last_run_date}
Agent version (from state.json): {agent_version}

You are running HEADLESS via the Claude Agent SDK — no interactive user is present.
Complete the entire pipeline autonomously and do not ask questions.

TOOL ACCESS (all via the Bash tool, run from the repo root):
  - Data tools:  python3 run_tools.py fred <SERIES_ID>
                 python3 run_tools.py cbuae
                 python3 run_tools.py opec
                 python3 run_tools.py worldbank AE <INDICATOR>
  - Web search:  python3 run_tools.py search "<query>"   ← the built-in WebSearch tool
                 is NOT available in this deployment; use this command (or WebFetch on a
                 specific URL) for all web lookups.
  - Calculations: run real Python via Bash (python3 - <<'EOF' ... EOF) for every
                  calculation — never do arithmetic mentally.
  - Files: use Write to save the brief to outputs/, and Read/Edit/Write to update
           outputs/state.json.

Follow the pipeline below exactly. All CLAUDE.md hard constraints apply.

────────────────────────────────────────────────────────────────────────────
{command_body}"""
    return header


def find_new_brief(since: float) -> Path | None:
    """Newest outputs/brief_v*_*.md created/modified during this run."""
    candidates = [
        p for p in OUTPUTS_DIR.glob("brief_v*_*.md")
        if p.stat().st_mtime >= since - 2
    ]
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def ensure_state_last_run(brief_path: Path, agent_version: str) -> None:
    """Fallback: guarantee state.json.last_run points at the brief, like run_agent.py."""
    state = load_state()
    lr = state.get("last_run", {})
    if lr.get("brief_path", "").endswith(brief_path.name):
        log("state.json updated by agent")
        return
    now = datetime.now()
    state.setdefault("last_run", {}).update({
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat(),
        "brief_path": str(brief_path.relative_to(ROOT)),
        "agent_version": f"v{agent_version.lstrip('v')}",
    })
    state["last_updated"] = now.strftime("%Y-%m-%d")
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str))
    log("state.json updated (fallback — agent did not set last_run)")


def _fmt_tool(block: ToolUseBlock) -> str:
    inp = block.input or {}
    if block.name == "Bash":
        return f"Bash: {str(inp.get('command', ''))[:120]}"
    if block.name in ("Write", "Edit"):
        return f"{block.name}: {inp.get('file_path', '')}"
    if block.name == "WebFetch":
        return f"WebFetch: {inp.get('url', '')}"
    return f"{block.name}: {json.dumps(inp)[:100]}"


async def run() -> Path | None:
    if not _OR_KEY:
        raise SystemExit("ERROR: OPENROUTER_API_KEY is not set.")

    state = load_state()
    agent_version = state.get("agent_version", "v2")
    log(f"EDB Agent SDK runner | model: {MODEL} | last run: "
        f"{state.get('last_run', {}).get('date', 'N/A')} | max_turns: {MAX_TURNS}")

    opts = ClaudeAgentOptions(
        model=MODEL,
        allowed_tools=ALLOWED_TOOLS,
        disallowed_tools=["WebSearch"],
        permission_mode="bypassPermissions",
        cwd=str(ROOT),
        setting_sources=["project"],   # loads CLAUDE.md + .claude/commands
        max_turns=MAX_TURNS,
        max_budget_usd=MAX_BUDGET_USD,
    )

    start = time.time()
    async for msg in query(prompt=build_prompt(state), options=opts):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    log(f"  → {_fmt_tool(b)}")
                elif isinstance(b, TextBlock):
                    text = b.text.strip()
                    if text:
                        log(f"  {text[:200]}")
        elif isinstance(msg, ResultMessage):
            log(f"done | turns={getattr(msg, 'num_turns', '?')} "
                f"duration={getattr(msg, 'duration_ms', '?')}ms "
                f"cost_usd={getattr(msg, 'total_cost_usd', '?')} "
                f"is_error={getattr(msg, 'is_error', '?')}")

    brief_path = find_new_brief(start)
    if brief_path:
        log(f"brief detected: {brief_path.name}")
        ensure_state_last_run(brief_path, agent_version)
    return brief_path


def main() -> None:
    brief_path = asyncio.run(run())
    if not brief_path or not brief_path.exists():
        print("ERROR: Agent did not produce a brief.", file=sys.stderr)
        sys.exit(1)

    summary = {
        "status": "success",
        "brief_name": brief_path.name,
        "brief_path": str(brief_path.relative_to(ROOT)),
        "model": MODEL,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }
    print(f"\nSUMMARY_JSON={json.dumps(summary)}", flush=True)


if __name__ == "__main__":
    main()
