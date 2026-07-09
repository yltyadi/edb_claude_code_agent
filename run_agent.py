#!/usr/bin/env python3
"""
EDB Macro Intelligence Agent — agentic loop runner.

Replaces the one-shot approach with a proper multi-turn tool-calling loop.
Claude decides which data tools to call, in what order, sees each result,
and adapts before writing the brief — matching Claude Code's interactive quality.

Usage:
  OPENROUTER_API_KEY=xxx FRED_API_KEY=xxx python run_agent.py
  OPENROUTER_MODEL=google/gemini-2.5-pro python run_agent.py
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")

ROOT = Path(__file__).parent
STATE_PATH = ROOT / "outputs" / "state.json"
CLAUDE_MD_PATH = ROOT / "CLAUDE.md"
OUTPUTS_DIR = ROOT / "outputs"

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-6")
MAX_TURNS = 40  # safety cap — a full run typically uses ~20–25 turns


# ── Tool definitions (OpenRouter / OpenAI tool-use format) ────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_state",
            "description": (
                "Read outputs/state.json — the cross-session memory containing baselines "
                "(yesterday's key figures), streaks (consecutive unchanged days), and last_run "
                "metadata. Call this first to get temporal context for streak language."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_fred",
            "description": (
                "Fetch a FRED economic data series. Returns JSON with the latest value, "
                "its date, and recent observations. Always check the value date — flag stale "
                "series (value date > 7 days before today) and web-search a fresh figure."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "series_id": {
                        "type": "string",
                        "description": (
                            "FRED series ID. Available: FEDFUNDS (Fed Funds Rate), DGS10 "
                            "(10-yr Treasury), DCOILBRENTEU (Brent crude), DCOILWTICO (WTI), "
                            "INDPRO (US Industrial Production), CPIAUCSL (US CPI), "
                            "T10YIE (10-yr breakeven inflation)."
                        ),
                    }
                },
                "required": ["series_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_cbuae",
            "description": "Fetch the CBUAE Base Rate and most recent policy statement.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_opec",
            "description": "Fetch the OPEC basket price and UAE production quota.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_worldbank",
            "description": "Fetch a World Bank indicator for a country.",
            "parameters": {
                "type": "object",
                "properties": {
                    "country": {
                        "type": "string",
                        "description": "ISO country code — always 'AE' for UAE indicators.",
                    },
                    "indicator": {
                        "type": "string",
                        "description": (
                            "World Bank indicator code. Available: NY.GDP.MKTP.CD (UAE GDP), "
                            "NV.IND.TOTL.ZS (UAE industry % GDP), FP.CPI.TOTL.ZG (UAE inflation), "
                            "BX.KLT.DINV.CD.WD (UAE FDI inflows)."
                        ),
                    },
                },
                "required": ["country", "indicator"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for recent macro news. Use for: (1) fresh prices when a FRED "
                "series is stale, (2) FOMC / CBUAE decisions since last run, (3) OPEC cuts or "
                "production changes, (4) breaking signals in EDB's five priority sectors."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query — be specific, include dates where possible.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_brief",
            "description": (
                "Write the completed brief to disk. Call exactly once, after all data gathering "
                "and calculations are done. The content must be the full brief markdown."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The complete EDB brief in markdown format.",
                    }
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_state",
            "description": (
                "Update outputs/state.json with today's baselines, updated streaks, and "
                "signals_fired_last_run. Call after write_brief, using the data you gathered. "
                "Preserve all existing fields — only update the values you have fresh data for."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "object",
                        "description": (
                            "The full updated state object. Must include: baselines (today's key "
                            "figures), streaks (updated counts), signals_fired_last_run (list), "
                            "last_run (date, timestamp, brief_path, agent_version)."
                        ),
                    }
                },
                "required": ["state"],
            },
        },
    },
]


# ── Core helpers ──────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run_tool(args: list[str]) -> str:
    result = subprocess.run(
        [sys.executable, str(ROOT / "run_tools.py")] + args,
        capture_output=True, text=True, cwd=str(ROOT), timeout=30,
    )
    output = result.stdout.strip()
    if not output:
        return json.dumps({"error": result.stderr.strip() or "no output"})
    return output[:3000]


def web_search(query: str) -> str:
    sys.path.insert(0, str(ROOT))
    try:
        from tools.web_search import web_search as _search
        results = _search(query, max_results=5)
        return json.dumps(results, indent=2)[:2000]
    except Exception as e:
        return json.dumps([{"error": str(e)}])


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {"agent_version": "v2", "baselines": {}, "streaks": {}, "signals_fired_last_run": []}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str))


def save_brief(content: str, agent_version: str) -> Path:
    now = datetime.now()
    ver = agent_version.lstrip("v")
    filename = f"brief_v{ver}_{now.strftime('%Y-%m-%d_%H%M')}.md"
    path = OUTPUTS_DIR / filename
    OUTPUTS_DIR.mkdir(exist_ok=True)
    path.write_text(content)
    return path


# ── Tool execution ────────────────────────────────────────────────────────────

def execute_tool(name: str, args: dict, agent_version: str) -> tuple[str, Path | None]:
    """Execute a tool call. Returns (result_string, optional_brief_path)."""
    brief_path = None

    if name == "read_state":
        result = STATE_PATH.read_text() if STATE_PATH.exists() else json.dumps({})

    elif name == "run_fred":
        result = run_tool(["fred", args.get("series_id", "")])

    elif name == "run_cbuae":
        result = run_tool(["cbuae"])

    elif name == "run_opec":
        result = run_tool(["opec"])

    elif name == "run_worldbank":
        result = run_tool(["worldbank", args.get("country", "AE"), args.get("indicator", "")])

    elif name == "web_search":
        result = web_search(args.get("query", ""))

    elif name == "write_brief":
        brief_path = save_brief(args.get("content", ""), agent_version)
        result = json.dumps({"brief_path": str(brief_path), "brief_name": brief_path.name})

    elif name == "update_state":
        try:
            new_state = args.get("state", {})
            if isinstance(new_state, dict) and new_state.get("last_run"):
                save_state(new_state)
                result = json.dumps({"ok": True})
            else:
                result = json.dumps({"error": "Invalid state — missing last_run field"})
        except Exception as e:
            result = json.dumps({"error": str(e)})

    else:
        result = json.dumps({"error": f"Unknown tool: {name}"})

    return result, brief_path


def _fmt_args(name: str, args: dict) -> str:
    """Compact one-line display of tool arguments for the log."""
    if name == "write_brief":
        return f"content=<{len(args.get('content', ''))} chars>"
    if name == "update_state":
        return "state={...}"
    return ", ".join(f"{k}={json.dumps(v)[:50]}" for k, v in args.items())


# ── Task prompt ───────────────────────────────────────────────────────────────

def build_task_prompt(state: dict) -> str:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    last_run_date = state.get("last_run", {}).get("date", "2026-01-01")
    agent_version = state.get("agent_version", "v2")

    return f"""You are the EDB Macro Intelligence Agent ({agent_version}).
Current UTC datetime: {now_utc}
Last run date: {last_run_date}

Generate the complete EDB Daily Macro Intelligence Brief now.

Follow this sequence:
1. Call read_state() to load cross-session baselines and streaks for trend language.
2. Gather all macro data using the available tools:
   - run_fred: FEDFUNDS, DGS10, DCOILBRENTEU, DCOILWTICO, INDPRO, CPIAUCSL, T10YIE
   - run_cbuae(), run_opec()
   - run_worldbank("AE", "NY.GDP.MKTP.CD"), run_worldbank("AE", "NV.IND.TOTL.ZS")
   - run_worldbank("AE", "FP.CPI.TOTL.ZG"), run_worldbank("AE", "BX.KLT.DINV.CD.WD")
3. For any FRED series where the value date is > 7 days before today, call web_search \
to find a current figure before using it in calculations.
4. Search the web for breaking signals since {last_run_date} — especially Fed/FOMC, \
CBUAE policy, Brent/OPEC, and EDB's five priority sectors.
5. Write the complete brief following all CLAUDE.md instructions. All four required \
calculations must appear (EIBOR sensitivity, oil fiscal impact, petrochemical pass-through, \
Operation 300bn run-rate).
6. Call write_brief(content=...) with the full markdown.
7. Call update_state(state={{...}}) with today's baselines, updated streaks, \
signals_fired_last_run, and last_run metadata.

All CLAUDE.md hard constraints apply — including the header format, five-sector matrix, \
AED/USD peg chain, Sources section, and Methodology section."""


# ── Agentic loop ──────────────────────────────────────────────────────────────

def run_agentic_loop(system_prompt: str, task_prompt: str, agent_version: str) -> Path | None:
    """Run the multi-turn agentic tool-calling loop. Returns the brief Path when written."""
    if not OPENROUTER_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_KEY,
        default_headers={
            "HTTP-Referer": "https://github.com/edb-macro-agent",
            "X-Title": "EDB Macro Intelligence Agent",
        },
    )

    messages: list[dict] = [{"role": "user", "content": task_prompt}]
    brief_path: Path | None = None

    log(f"Agentic loop starting — model: {MODEL}, max turns: {MAX_TURNS}")

    for turn in range(MAX_TURNS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}] + messages,
            tools=TOOLS,
            max_tokens=16384,
            temperature=0.1,
        )
        choice = response.choices[0]
        msg = choice.message

        # Append assistant message to conversation history
        assistant_msg: dict = {"role": "assistant"}
        if msg.content:
            assistant_msg["content"] = msg.content
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_msg)

        if choice.finish_reason == "stop":
            log(f"Turn {turn + 1}: agent finished")
            break

        if choice.finish_reason != "tool_calls" or not msg.tool_calls:
            log(f"Turn {turn + 1}: unexpected finish_reason={choice.finish_reason!r}, stopping")
            break

        # Execute all tool calls in this turn
        tool_results = []
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except Exception:
                args = {}

            log(f"  [{turn + 1}] {name}({_fmt_args(name, args)})")
            result, bp = execute_tool(name, args, agent_version)

            if bp:
                brief_path = bp
                log(f"       → brief saved: {bp.name}")

            tool_results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        messages.extend(tool_results)

    else:
        log(f"WARNING: hit MAX_TURNS ({MAX_TURNS}) safety cap — brief may be incomplete")

    return brief_path


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if not OPENROUTER_KEY:
        print("ERROR: OPENROUTER_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    state = load_state()
    agent_version = state.get("agent_version", "v2").lstrip("v")
    last_run_date = state.get("last_run", {}).get("date", "N/A")
    log(f"EDB Macro Intelligence Agent v{agent_version} | model: {MODEL} | last run: {last_run_date}")

    system_prompt = CLAUDE_MD_PATH.read_text()
    task_prompt = build_task_prompt(state)

    brief_path = run_agentic_loop(system_prompt, task_prompt, agent_version)

    if not brief_path or not brief_path.exists():
        print("ERROR: Agent did not produce a brief.", file=sys.stderr)
        sys.exit(1)

    log(f"Brief saved → {brief_path.name}")

    # Reload state — Claude may have updated it via update_state tool
    state = load_state()

    # Fallback: ensure last_run is always set even if Claude skipped update_state
    if not state.get("last_run", {}).get("brief_path"):
        now = datetime.now()
        state.setdefault("last_run", {}).update({
            "date": now.strftime("%Y-%m-%d"),
            "timestamp": now.isoformat(),
            "brief_path": str(brief_path.relative_to(ROOT)),
            "agent_version": f"v{agent_version}",
        })
        state["last_updated"] = now.strftime("%Y-%m-%d")
        save_state(state)
        log("state.json updated (fallback — agent did not call update_state)")
    else:
        log("state.json updated by agent")

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
