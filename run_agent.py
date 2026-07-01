#!/usr/bin/env python3
"""
EDB Macro Intelligence Agent — standalone runner for GitHub Actions / any CI.
Replicates the /edb-brief Claude Code pipeline using any OpenAI-compatible API.

Usage:
  OPENROUTER_API_KEY=xxx FRED_API_KEY=xxx python run_agent.py
  OPENROUTER_MODEL=google/gemini-2.5-pro python run_agent.py   # override model
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
MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-5")

# All tool commands to run in sequence
TOOL_COMMANDS = [
    ("fedfunds",      ["fred", "FEDFUNDS"]),
    ("dgs10",         ["fred", "DGS10"]),
    ("brent",         ["fred", "DCOILBRENTEU"]),
    ("wti",           ["fred", "DCOILWTICO"]),
    ("indpro",        ["fred", "INDPRO"]),
    ("cpi",           ["fred", "CPIAUCSL"]),
    ("t10yie",        ["fred", "T10YIE"]),
    ("cbuae",         ["cbuae"]),
    ("opec",          ["opec"]),
    ("uae_gdp",       ["worldbank", "AE", "NY.GDP.MKTP.CD"]),
    ("uae_industry",  ["worldbank", "AE", "NV.IND.TOTL.ZS"]),
    ("uae_cpi",       ["worldbank", "AE", "FP.CPI.TOTL.ZG"]),
    ("uae_fdi",       ["worldbank", "AE", "BX.KLT.DINV.CD.WD"]),
]


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run_tool(args: list[str]) -> str:
    result = subprocess.run(
        [sys.executable, str(ROOT / "run_tools.py")] + args,
        capture_output=True, text=True, cwd=str(ROOT), timeout=30
    )
    output = result.stdout.strip()
    if not output:
        return json.dumps({"error": result.stderr.strip() or "no output"})
    return output[:3000]  # cap per-tool output to avoid token overflow


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


def gather_tool_data() -> dict:
    data = {}
    for key, args in TOOL_COMMANDS:
        log(f"  tool: {' '.join(args)}")
        try:
            data[key] = run_tool(args)
        except Exception as e:
            data[key] = json.dumps({"error": str(e)})
    return data


def gather_web_data(last_run_date: str) -> dict:
    queries = [
        f"Federal Reserve FOMC interest rate decision after:{last_run_date}",
        f"CBUAE UAE central bank monetary policy after:{last_run_date}",
        f"Brent crude oil price OPEC production after:{last_run_date}",
        f"UAE manufacturing industrial sector economy after:{last_run_date}",
        f"US CPI inflation PCE core after:{last_run_date}",
        f"UAE food security agriculture imports after:{last_run_date}",
        f"UAE renewables solar energy investment after:{last_run_date}",
    ]
    results = {}
    for q in queries:
        log(f"  search: {q[:70]}")
        results[q] = web_search(q)
    return results


def build_prompt(state: dict, tool_data: dict, search_data: dict) -> str:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    agent_version = state.get("agent_version", "v2").lstrip("v")
    last_run_date = state.get("last_run", {}).get("date", "N/A")
    baselines = state.get("baselines", {})
    streaks = state.get("streaks", {})
    signals_prior = state.get("signals_fired_last_run", [])

    parts = [
        "## OPERATIONAL CONTEXT",
        "You are operating via standalone API (not Claude Code).",
        "All data gathering has been completed. DO NOT attempt to call tools or run code.",
        "Your ONLY task is to write the brief using the data below.",
        "All CLAUDE.md hard constraints still apply — including all four required calculations.",
        "",
        f"**Current UTC datetime:** {now_utc}",
        f"**Agent version:** v{agent_version}",
        f"**Last run date:** {last_run_date}",
        "",
        "## PRIOR-RUN STATE (from state.json)",
        "Use these for streak language and trend comparisons:",
        f"```json",
        f"baselines: {json.dumps(baselines, indent=2)}",
        f"streaks:   {json.dumps(streaks, indent=2)}",
        f"signals_fired_last_run: {json.dumps(signals_prior)}",
        "```",
        "",
        "## LIVE DATA TOOL OUTPUTS",
        "(Use these as your primary quantitative inputs. Flag any null/error series.)",
    ]

    for key, output in tool_data.items():
        parts.append(f"\n### Tool: {key}\n```json\n{output}\n```")

    parts.append("\n## WEB SEARCH RESULTS (breaking signals since last run)")
    parts.append("Classify each signal as [NEW] if after last_run_date, or [CONTINUING] if already in signals_fired_last_run.\n")
    for query, result in search_data.items():
        parts.append(f"\n### Query: `{query}`\n```json\n{result}\n```")

    parts.append("""
## YOUR TASK

Write the complete EDB Daily Macro Intelligence Brief now.

**FORMAT — copy this header block exactly:**
```
---
# EDB Daily Macro Intelligence Brief
**Date:** {full weekday, DD Month YYYY}
**Agent version:** v{N}
**Generated:** {HH:MM UTC}
**Signals processed:** {N}
**Signals passing mandate filter:** {N}

---
```
Then continue with:
1. `## Executive Brief (Type A)` — **Headline:** (one sentence with [NEW]/[CONTINUING] labels), 2–3 para body with trend language from state.json streaks, sector impact matrix (all 5 rows, every row data-justified), **Key number:** (one AED figure), **Watch list — next 72 hours:** (3 named events)
2. `## Credit Team Alert (Type B)` — signal, portfolio exposure, calculation block with ALL FOUR required calcs:
   - **EIBOR ADS ±25/50bps:** First line of block must be `EIBOR source: estimated (...)`. Scenario lines must use format `+25bps scenario: AED X (Δ AED Y)` — no space between `+25` and `bps`.
   - **Oil fiscal calc:** First output line must be `UAE oil revenue impact: AED X` — then show ×3.6725 FX step and annual figure.
   - **Petrochemical pass-through:** 60% rate × AED 17.5bn feedstock × Brent delta → AED result.
   - **Op300bn run-rate:** (current−133)/(300−133) gap method — not current/300.
   Scenario table: compact 2-row (Base case | Reversal) within 150 chars. Action flag with team/threshold/milestone.
3. `## Stakeholder Bulletin (Type C)` — What happened / What it means / What businesses should consider
4. `*Sources:*` and `*Methodology:*` sections — EIBOR estimation basis must appear in the calc block AND here

Do NOT add YAML frontmatter. Start the output with `---` (a plain horizontal rule), then the `#` heading.
Output ONLY the brief markdown — no preamble, no explanation.
""")

    return "\n".join(parts)


def call_llm(system_prompt: str, user_prompt: str) -> str:
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

    log(f"Calling LLM ({MODEL}) — this takes ~60–120 seconds...")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=16384,
        temperature=0.1,
    )
    return response.choices[0].message.content


def save_brief(content: str, agent_version: str) -> Path:
    now = datetime.now()
    # agent_version may be "v2" or "2" — normalise to just the number
    ver = agent_version.lstrip("v")
    filename = f"brief_v{ver}_{now.strftime('%Y-%m-%d_%H%M')}.md"
    path = OUTPUTS_DIR / filename
    OUTPUTS_DIR.mkdir(exist_ok=True)
    path.write_text(content)
    return path


def update_state(state: dict, brief_path: Path) -> None:
    now = datetime.now()
    agent_version = state.get("agent_version", "v2")

    state["last_updated"] = now.strftime("%Y-%m-%d")
    state["last_run"] = {
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat(),
        "brief_path": str(brief_path.relative_to(ROOT)),
        "agent_version": agent_version,
    }

    streaks = state.get("streaks", {})
    streaks["eibor_unchanged_days"] = streaks.get("eibor_unchanged_days", 0) + 1
    state["streaks"] = streaks

    save_state(state)


def main() -> None:
    if not OPENROUTER_KEY:
        print("ERROR: OPENROUTER_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    log(f"EDB Macro Intelligence Agent — model: {MODEL}")

    state = load_state()
    last_run_date = state.get("last_run", {}).get("date", "2026-01-01")
    agent_version = state.get("agent_version", "v2").lstrip("v")
    log(f"Agent v{agent_version} | Last run: {last_run_date}")

    log("Gathering live data from tools...")
    tool_data = gather_tool_data()

    log("Running web searches...")
    search_data = gather_web_data(last_run_date)

    system_prompt = CLAUDE_MD_PATH.read_text()
    user_prompt = build_prompt(state, tool_data, search_data)

    brief_content = call_llm(system_prompt, user_prompt)

    brief_path = save_brief(brief_content, agent_version)
    log(f"Brief saved → {brief_path.name}")

    update_state(state, brief_path)
    log("state.json updated")

    # Emit machine-readable summary for GitHub Actions to capture
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
