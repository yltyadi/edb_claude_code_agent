#!/usr/bin/env python3
"""
EDB Macro Intelligence — HuggingFace Spaces frontend.

Tab 1 — Daily Brief: generate, browse, streaming Q&A chat
Tab 2 — Evaluation: run rubric eval (auto checks + LLM judging), score history

Required HF Space secrets:
  OPENROUTER_API_KEY  — OpenRouter key (required)
  FRED_API_KEY        — FRED API key (required for brief generation)
  GITHUB_TOKEN        — PAT with repo write access (required)
  GITHUB_REPO         — e.g. "yltyadi/edb-macro-agent-v2" (required)
"""

import asyncio
import base64
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import requests

# ── HuggingFace Hub compat patch ─────────────────────────────────────────────
# Gradio 4–5 early versions import HfFolder which was removed in huggingface_hub 0.26+.
# We don't use HF OAuth (secrets come from Space env vars), so a no-op stub is fine.
try:
    from huggingface_hub import HfFolder  # noqa: F401
except ImportError:
    import huggingface_hub as _hf
    import types as _types
    _hf.HfFolder = _types.SimpleNamespace(  # type: ignore[attr-defined]
        get_token=lambda: None,
        save_token=lambda token: None,
        delete_token=lambda: None,
    )

import gradio as gr
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

_GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
_GITHUB_REPO  = os.environ.get("GITHUB_REPO", "")
_OR_KEY       = os.environ.get("OPENROUTER_API_KEY", "")
MODEL         = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-6")
CHAT_MODEL    = os.environ.get("OPENROUTER_CHAT_MODEL", "anthropic/claude-haiku-4-5")

# Load rubric (available in repo at eval/rubric.py)
try:
    from eval.rubric import (
        AUTOMATED_CHECKS, LLM_DIMENSIONS,
        DIMENSION_WEIGHTS, AUTO_WEIGHT, LLM_WEIGHT,
    )
    _RUBRIC_OK = True
except ImportError:
    _RUBRIC_OK = False

# ── GitHub helpers ────────────────────────────────────────────────────────────
def _gh_headers():
    return {"Authorization": f"token {_GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}

def gh_get(path: str) -> tuple:
    r = requests.get(f"https://api.github.com/repos/{_GITHUB_REPO}/contents/{path}",
                     headers=_gh_headers(), timeout=20)
    if r.ok:
        d = r.json()
        return base64.b64decode(d["content"]).decode(), d["sha"]
    return None, None

def gh_put(path: str, content: str, sha, message: str) -> bool:
    payload = {"message": message,
               "content": base64.b64encode(content.encode()).decode()}
    if sha:
        payload["sha"] = sha
    r = requests.put(f"https://api.github.com/repos/{_GITHUB_REPO}/contents/{path}",
                     headers={**_gh_headers(), "Content-Type": "application/json"},
                     json=payload, timeout=20)
    return r.status_code in (200, 201)

def gh_open_issue(title: str, body: str) -> tuple[bool, object]:
    """Create a GitHub issue to trigger the matching Actions workflow.

    The Space is a trigger-and-view frontend: all compute (brief generation, evals)
    runs in GitHub Actions — where Node + the Claude Agent SDK are available — not on
    the Python-only Space. Each workflow fires on an issue with a specific title.
    Returns (ok, issue_number_or_error_message).
    """
    if not _GITHUB_TOKEN or not _GITHUB_REPO:
        return False, "GITHUB_TOKEN / GITHUB_REPO not set in Space secrets."
    r = requests.post(
        f"https://api.github.com/repos/{_GITHUB_REPO}/issues",
        headers={**_gh_headers(), "Content-Type": "application/json"},
        json={"title": title, "body": body}, timeout=20,
    )
    if r.status_code in (200, 201):
        return True, r.json().get("number")
    return False, f"HTTP {r.status_code}: {r.text[:200]}"


def _trigger_and_report(title: str, body: str, workflow_file: str, what: str, eta: str):
    """Shared handler: open the trigger issue and yield a status message + no viewer change."""
    ok, res = gh_open_issue(title, body)
    actions = f"https://github.com/{_GITHUB_REPO}/actions/workflows/{workflow_file}"
    if not ok:
        return f"❌ Could not trigger {what}: {res}", gr.update()
    return (
        f"🚀 Triggered **{what}** in GitHub Actions (issue #{res}).\n\n"
        f"It runs on a full Node + Claude Agent SDK runner and commits the result "
        f"to the repo when done ({eta}).\n\n"
        f"• Watch progress: {actions}\n"
        f"• When it finishes, click 🔄 to refresh — the new output loads from GitHub."
    ), gr.update()


def _list_outputs(pattern: str) -> list:
    r = requests.get(f"https://api.github.com/repos/{_GITHUB_REPO}/contents/outputs",
                     headers=_gh_headers(), timeout=15)
    if not r.ok:
        return []
    pat = re.compile(pattern)
    return sorted([f["name"] for f in r.json()
                   if isinstance(f, dict) and pat.match(f.get("name", ""))], reverse=True)

def list_briefs():
    return _list_outputs(r"brief_v\d+_\d{4}-\d{2}-\d{2}_\d{4}\.md")

def list_evals():
    return _list_outputs(r"eval_\d{4}-\d{2}-\d{2}.*\.md")

# ── OpenRouter client ─────────────────────────────────────────────────────────
def _client(model: str = MODEL) -> OpenAI | None:
    if not _OR_KEY:
        return None
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=_OR_KEY,
        default_headers={
            "HTTP-Referer": f"https://huggingface.co/spaces/{_GITHUB_REPO}",
            "X-Title": "EDB Macro Intelligence Agent",
        },
    )

# ── Tab 1 — Brief generation ──────────────────────────────────────────────────

def _sync_state():
    content, _ = gh_get("outputs/state.json")
    if content:
        Path("outputs").mkdir(exist_ok=True)
        Path("outputs/state.json").write_text(content)

def _push_run(brief_path: str, date: str) -> bool:
    ok = True
    _, sha = gh_get(brief_path)
    ok = gh_put(brief_path, Path(brief_path).read_text(), sha,
                f"brief: {date} [HF Spaces]") and ok
    state_p = Path("outputs/state.json")
    if state_p.exists():
        _, s_sha = gh_get("outputs/state.json")
        ok = gh_put("outputs/state.json", state_p.read_text(), s_sha,
                    f"state: {date} [HF Spaces]") and ok
    return ok

def run_brief():
    # Triggers the Claude Agent SDK generation workflow in GitHub Actions (the Space
    # itself has no Node/CLI, so it can't run the SDK locally). CI generates the brief
    # and commits it; refresh the dropdown to view it.
    yield _trigger_and_report(
        title="Generate Brief",
        body="Triggered from the Hugging Face Space. Runs run_agent_sdk.py (Claude Agent SDK) "
             "in GitHub Actions and commits the brief to outputs/.",
        workflow_file="generate_brief.yml",
        what="the SDK brief generation",
        eta="~3–6 min",
    )

def refresh_brief_dropdown():
    briefs = list_briefs()
    return gr.Dropdown(choices=briefs, value=briefs[0] if briefs else None)

def load_brief(name: str) -> str:
    if not name:
        return ""
    content, _ = gh_get(f"outputs/{name}")
    return content or f"*(Could not load `{name}` from GitHub.)*"

# ── Tab 2 — Evaluation ────────────────────────────────────────────────────────

def _run_auto_checks(content: str | None) -> dict:
    if not content or not _RUBRIC_OK:
        return {}
    return {c["id"]: bool(re.search(c["pattern"], content)) for c in AUTOMATED_CHECKS}

def _fmt_check(val: bool) -> str:
    return "✓" if val else "✗"

def _score_auto(checks: dict) -> float:
    if not checks:
        return 0.0
    return sum(checks.values()) / len(checks) * 100 * AUTO_WEIGHT

def _score_llm(dims: dict) -> float:
    if not dims or not _RUBRIC_OK:
        return 0.0
    total = sum(dims.get(d["id"], 0) * d["weight"] for d in LLM_DIMENSIONS)
    return total / 5 * 100 * LLM_WEIGHT

def _build_eval_prompt(v2_brief: str, v1_brief: str, gen_brief: str) -> str:
    def excerpt(text, n=3500):
        if not text:
            return "(not available)"
        if len(text) <= n:
            return text
        return text[:2500] + "\n\n[…truncated…]\n\n" + text[-1000:]

    dims_desc = "\n".join(
        f"{i+1}. {d['name']} ({int(d['weight']*100)}%): {d['description'][:200]}"
        for i, d in enumerate(LLM_DIMENSIONS)
    )

    return f"""You are evaluating three macro intelligence briefs for Emirates Development Bank.
Score each brief 1–5 on each dimension (1=worst, 5=best).

IMPORTANT NOTE on Trend & Continuity: v1 and General briefs have no cross-session state.json access.
They are structurally capped at 2/5 for Trend & Continuity regardless of prose quality.

DIMENSIONS:
{dims_desc}

--- BRIEF 1: v2 Agent (cross-session memory, streak language, CLAUDE.md feedback loop) ---
{excerpt(v2_brief)}

--- BRIEF 2: v1 Agent (EDB-structured pipeline, no cross-session memory) ---
{excerpt(v1_brief)}

--- BRIEF 3: General Agent (baseline Claude, no EDB tools or format) ---
{excerpt(gen_brief)}

Respond with ONLY valid JSON:
{{
  "v2":      {{"mandate_relevance":N,"data_grounding":N,"quantitative_accuracy":N,"structure_completeness":N,"action_specificity":N,"data_integrity":N,"trend_continuity":N}},
  "v1":      {{"mandate_relevance":N,"data_grounding":N,"quantitative_accuracy":N,"structure_completeness":N,"action_specificity":N,"data_integrity":N,"trend_continuity":N}},
  "general": {{"mandate_relevance":N,"data_grounding":N,"quantitative_accuracy":N,"structure_completeness":N,"action_specificity":N,"data_integrity":N,"trend_continuity":N}},
  "reasoning": {{
    "v2": "2-3 sentence summary of v2 brief quality",
    "v1": "2-3 sentence summary of v1 brief quality",
    "general": "2-3 sentence summary of general brief quality"
  }}
}}"""

def _format_eval_report(
    date_str: str,
    v2_name: str, v1_name: str, gen_name: str,
    v2_checks: dict, v1_checks: dict, gen_checks: dict,
    llm_scores: dict,
) -> str:
    v2_auto = sum(v2_checks.values()) if v2_checks else 0
    v1_auto = sum(v1_checks.values()) if v1_checks else 0
    gen_auto = sum(gen_checks.values()) if gen_checks else 0
    n = len(AUTOMATED_CHECKS) if _RUBRIC_OK else 20

    v2_dims  = llm_scores.get("v2", {})
    v1_dims  = llm_scores.get("v1", {})
    gen_dims = llm_scores.get("general", {})

    def llm_pct(dims):
        if not dims or not _RUBRIC_OK:
            return 0.0
        return sum(dims.get(d["id"], 0) * d["weight"] for d in LLM_DIMENSIONS) / 5

    v2_final  = (v2_auto / n * AUTO_WEIGHT  + llm_pct(v2_dims)  * LLM_WEIGHT) * 100 if _RUBRIC_OK else 0
    v1_final  = (v1_auto / n * AUTO_WEIGHT  + llm_pct(v1_dims)  * LLM_WEIGHT) * 100 if _RUBRIC_OK else 0
    gen_final = (gen_auto / n * AUTO_WEIGHT + llm_pct(gen_dims) * LLM_WEIGHT) * 100 if _RUBRIC_OK else 0

    # Auto checks table
    rows = ""
    if _RUBRIC_OK:
        for c in AUTOMATED_CHECKS:
            rows += (f"| {c['name']:<50} | {_fmt_check(v2_checks.get(c['id'], False))} "
                     f"| {_fmt_check(v1_checks.get(c['id'], False))} "
                     f"| {_fmt_check(gen_checks.get(c['id'], False))} |\n")

    # LLM dims table
    dim_rows = ""
    if _RUBRIC_OK:
        for d in LLM_DIMENSIONS:
            dim_rows += (f"| {d['name']:<28} | {int(d['weight']*100)}% "
                         f"| {v2_dims.get(d['id'], '—')}/5 "
                         f"| {v1_dims.get(d['id'], '—')}/5 "
                         f"| {gen_dims.get(d['id'], '—')}/5 |\n")

    reasoning = llm_scores.get("reasoning", {})

    return f"""# EDB Agent Evaluation Report
**Date:** {date_str}
**v2 brief:** outputs/{v2_name}
**v1 brief:** outputs/{v1_name or '(none)'}
**General brief:** outputs/{gen_name or '(none)'}
**Rubric version:** v2 ({n} automated checks, 7 LLM dimensions)
**Generated by:** HF Spaces eval runner

---

## Automated Checks (40% of score)

| Check | v2 | v1 | General |
|-------|:--:|:--:|:-------:|
{rows}| **TOTAL** | **{v2_auto}/{n}** | **{v1_auto}/{n}** | **{gen_auto}/{n}** |

---

## LLM Dimensions (60% of score)

| Dimension | Wt | v2 | v1 | General |
|-----------|:--:|:--:|:--:|:-------:|
{dim_rows}

### Reasoning

**v2 Agent:** {reasoning.get('v2', '—')}

**v1 Agent:** {reasoning.get('v1', '—')}

**General Agent:** {reasoning.get('general', '—')}

---

## Final Scores

|                      | v2 Agent | v1 Agent | General |
|----------------------|:--------:|:--------:|:-------:|
| Automated (40%)      | {v2_auto/n*40:.1f}    | {v1_auto/n*40:.1f}    | {gen_auto/n*40:.1f}   |
| LLM Dimensions (60%) | {llm_pct(v2_dims)*60:.1f}    | {llm_pct(v1_dims)*60:.1f}    | {llm_pct(gen_dims)*60:.1f}   |
| **Final Score**      | **{v2_final:.1f} / 100** | **{v1_final:.1f} / 100** | **{gen_final:.1f} / 100** |
| **v2 vs v1**         | **{v2_final-v1_final:+.1f} pts** | | |
| **v2 vs General**    | **{v2_final-gen_final:+.1f} pts** | | |
"""

def run_eval():
    # Triggers the Legacy evaluation workflow in GitHub Actions (deliberate, button-only —
    # not on the daily schedule). CI runs the 20 checks + one LLM-judge call and commits.
    yield _trigger_and_report(
        title="Run Legacy Eval",
        body="Triggered from the Hugging Face Space. Runs eval/run_eval.py (legacy framework: "
             "20 checks + one-call LLM judging) in GitHub Actions and commits the report.",
        workflow_file="run_legacy_eval.yml",
        what="the Legacy evaluation",
        eta="~1–2 min",
    )
def refresh_eval_dropdown():
    evals = list_evals()
    return gr.Dropdown(choices=evals, value=evals[0] if evals else None)

def load_eval(name: str) -> str:
    if not name:
        return ""
    content, _ = gh_get(f"outputs/{name}")
    return content or f"*(Could not load `{name}`.)*"

# ── Tab 3 — AutoRubric evaluation (analytic, atomic per-criterion) ─────────────

def list_autorubric_evals():
    return _list_outputs(r"eval_autorubric_\d{4}-\d{2}-\d{2}.*\.md")

def refresh_autorubric_dropdown():
    evals = list_autorubric_evals()
    return gr.Dropdown(choices=evals, value=evals[0] if evals else None)

def load_autorubric_eval(name: str) -> str:
    if not name:
        return ""
    content, _ = gh_get(f"outputs/{name}")
    return content or f"*(Could not load `{name}`.)*"

def run_autorubric_eval():
    # Triggers the AutoRubric evaluation workflow in GitHub Actions (also closes the
    # CLAUDE.md self-improvement loop via --patch-claude-md). CI grades + commits.
    yield _trigger_and_report(
        title="Run AutoRubric Eval",
        body="Triggered from the Hugging Face Space. Runs the AutoRubric ensemble eval in "
             "GitHub Actions and commits the report + updated state.json.",
        workflow_file="run_eval.yml",
        what="the AutoRubric evaluation",
        eta="~2–3 min",
    )
def _latest_autorubric_eval():
    """Return the most recent autorubric_eval_history entry, or None."""
    try:
        state_raw, _ = gh_get("outputs/state.json")
        if not state_raw:
            return None
        history = json.loads(state_raw).get("autorubric_eval_history", [])
        if not history:
            return None
        return sorted(history, key=lambda e: e.get("eval_date", ""))[-1]
    except Exception:
        return None


def make_autorubric_comparison_chart():
    """Cross-agent comparison: final scores + per-dimension breakdown from latest eval."""
    fig_bg = "#0f1117"
    ax_bg  = "#0d0d1a"

    latest = _latest_autorubric_eval()

    if latest is None:
        fig, ax = plt.subplots(figsize=(10, 4), facecolor=fig_bg)
        ax.set_facecolor(ax_bg)
        ax.text(0.5, 0.5, "No AutoRubric evals yet.\nRun one below to compare agents.",
                ha="center", va="center", color="#888888", fontsize=12,
                transform=ax.transAxes)
        ax.axis("off")
        fig.tight_layout()
        return fig

    scores = latest.get("scores", {})
    deltas = latest.get("deltas", {})
    agents = ["v2", "v1", "general"]
    labels = {"v2": "v2 Custom Agent", "v1": "v1 Custom Agent", "general": "General Agent"}
    colors = {"v2": "#4fc3f7", "v1": "#ffb74d", "general": "#ef5350"}

    dim_ids   = [d["id"] for d in LLM_DIMENSIONS]
    dim_short = [
        d["name"].replace("& Source Citation", "").replace("& Calculation Discipline", "")
                 .replace("& Gap Disclosure", "").replace("& Continuity", "").strip()
        for d in LLM_DIMENSIONS
    ]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(14, 5.5),
        gridspec_kw={"width_ratios": [2, 3]},
        facecolor=fig_bg,
    )

    # ── Left panel: final score horizontal bars ──────────────────────────────
    ax1.set_facecolor(ax_bg)
    rev_agents = list(reversed(agents))
    final_vals = [scores.get(a, {}).get("final_score") or 0 for a in rev_agents]
    bars = ax1.barh(
        [labels[a] for a in rev_agents], final_vals,
        color=[colors[a] for a in rev_agents], height=0.45, zorder=3,
    )
    for bar, a, val in zip(bars, rev_agents, final_vals):
        ax1.text(min(val + 1.5, 107), bar.get_y() + bar.get_height() / 2,
                 f"{val:.1f}/100", va="center", color="white",
                 fontsize=11, fontweight="bold")
    ax1.set_xlim(0, 115)
    ax1.set_xlabel("Score / 100", color="#aaaaaa", fontsize=9)
    ax1.set_title("Overall Score", color="white", fontsize=12, pad=8)
    ax1.tick_params(colors="#cccccc", labelsize=9)
    ax1.spines[:].set_color("#333344")
    ax1.grid(axis="x", color="#222233", linewidth=0.5, zorder=0)
    if "v2_vs_gen" in deltas:
        ax1.text(0.98, 0.04,
                 f"v2 leads General by +{deltas['v2_vs_gen']:.0f} pts",
                 transform=ax1.transAxes, ha="right", va="bottom",
                 color="#4fc3f7", fontsize=8, style="italic")

    # ── Right panel: per-dimension grouped bars ──────────────────────────────
    ax2.set_facecolor(ax_bg)
    x     = np.arange(len(dim_ids))
    width = 0.25
    for i, a in enumerate(agents):
        dim_vals = [scores.get(a, {}).get("dims", {}).get(did) or 0 for did in dim_ids]
        ax2.bar(x + i * width, dim_vals, width,
                label=labels[a], color=colors[a], alpha=0.85, zorder=3)
    ax2.set_xticks(x + width)
    ax2.set_xticklabels(dim_short, rotation=28, ha="right",
                        color="#cccccc", fontsize=8)
    ax2.set_ylim(0, 5.8)
    ax2.set_ylabel("Score (1–5)", color="#aaaaaa", fontsize=9)
    ax2.set_title("Per-Dimension Breakdown", color="white", fontsize=12, pad=8)
    ax2.tick_params(colors="#cccccc", labelsize=8)
    ax2.spines[:].set_color("#333344")
    ax2.grid(axis="y", color="#222233", linewidth=0.5, zorder=0)
    ax2.axhline(y=3, color="#555566", linestyle="--", alpha=0.6, linewidth=0.8)
    ax2.legend(facecolor="#1a1a2e", edgecolor="#333344",
               labelcolor="#cccccc", fontsize=8, loc="upper right")

    eval_date = latest.get("eval_date", "")
    judge_str = ", ".join(j.split("/")[-1] for j in latest.get("judges", []))
    fig.suptitle(
        f"EDB Agent Comparison — AutoRubric  ({eval_date}  ·  judges: {judge_str})",
        color="white", fontsize=10, y=1.01,
    )
    plt.tight_layout(pad=1.5)
    return fig


def make_autorubric_summary_md():
    """Score card + 'why custom agent?' narrative from the latest eval."""
    latest = _latest_autorubric_eval()
    if latest is None:
        return "_No eval yet — run one below._"

    scores = latest.get("scores", {})
    deltas = latest.get("deltas", {})
    date   = latest.get("eval_date", "unknown")
    judges = latest.get("judges", [])
    judge_str = " + ".join(j.split("/")[-1] for j in judges)

    def fs(t): return scores.get(t, {}).get("final_score", "—")
    def bp(t):
        b = scores.get(t, {}).get("binary", {})
        passed = sum(1 for v in b.values() if v)
        return f"{passed}/{len(b)}" if b else "—"

    gap = deltas.get("v2_vs_gen")
    gap_line = (
        f"The custom v2 agent outperforms a general-purpose LLM by **+{gap:.0f} points** "
        f"on EDB's specialised rubric."
        if gap is not None else ""
    )

    return (
        f"**Latest evaluation — {date}** ·  judges: {judge_str}\n\n"
        f"| Agent | Final score | Structural checks | Why it matters |\n"
        f"|---|:---:|:---:|---|\n"
        f"| 🥇 **v2 Custom Agent** | **{fs('v2')}/100** | {bp('v2')} | Full pipeline: live data tools, state.json streaks, EIBOR chain, sector matrix |\n"
        f"| 🥈 v1 Custom Agent | {fs('v1')}/100 | {bp('v1')} | Custom prompting + sector mapping, no cross-session memory |\n"
        f"| ❌ General Agent | {fs('general')}/100 | {bp('general')} | Off-the-shelf assistant with no EDB context, tools, or calculation templates |\n\n"
        f"{gap_line}\n\n"
        # f"> **Why does an analyst need this custom agent?** A standard LLM assistant cannot: "
        # f"(1) fetch live macro data via FRED/CBUAE/OPEC APIs, "
        # f"(2) trace the AED/USD peg chain through to EIBOR and EDB's SME loan portfolio, "
        # f"(3) maintain cross-session baselines for trend language (\"unchanged for 187 days\"), "
        # f"(4) map every signal to EDB's five priority sectors with quantified impact. "
        # f"The score gap quantifies exactly what the custom engineering delivers."
    )

def _latest_legacy_eval():
    """Return the most recent eval_history entry, or None."""
    try:
        state_raw, _ = gh_get("outputs/state.json")
        if not state_raw:
            return None
        history = json.loads(state_raw).get("eval_history", [])
        if not history:
            return None
        return sorted(history, key=lambda e: e.get("eval_date", ""))[-1]
    except Exception:
        return None


def _comparison_chart(latest, dim_key: str, title_suffix: str):
    """Shared chart builder for both eval tabs. dim_key is 'dims' or 'dimension_scores'."""
    fig_bg = "#0f1117"
    ax_bg  = "#0d0d1a"

    if latest is None:
        fig, ax = plt.subplots(figsize=(10, 4), facecolor=fig_bg)
        ax.set_facecolor(ax_bg)
        ax.text(0.5, 0.5, "No evaluations yet.\nRun one below to compare agents.",
                ha="center", va="center", color="#888888", fontsize=12,
                transform=ax.transAxes)
        ax.axis("off")
        fig.tight_layout()
        return fig

    scores  = latest.get("scores", {})
    deltas  = latest.get("deltas", {})
    agents  = ["v2", "v1", "general"]
    labels  = {"v2": "v2 Custom Agent", "v1": "v1 Custom Agent", "general": "General Agent"}
    colors  = {"v2": "#4fc3f7", "v1": "#ffb74d", "general": "#ef5350"}
    dim_ids = [d["id"] for d in LLM_DIMENSIONS]
    dim_short = [
        d["name"].replace("& Source Citation", "").replace("& Calculation Discipline", "")
                 .replace("& Gap Disclosure", "").replace("& Continuity", "").strip()
        for d in LLM_DIMENSIONS
    ]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(14, 5.5),
        gridspec_kw={"width_ratios": [2, 3]},
        facecolor=fig_bg,
    )

    # ── Left: final score horizontal bars ────────────────────────────────────
    ax1.set_facecolor(ax_bg)
    rev = list(reversed(agents))
    final_vals = [scores.get(a, {}).get("final_score") or 0 for a in rev]
    bars = ax1.barh(
        [labels[a] for a in rev], final_vals,
        color=[colors[a] for a in rev], height=0.45, zorder=3,
    )
    for bar, a, val in zip(bars, rev, final_vals):
        ax1.text(min(val + 1.5, 107), bar.get_y() + bar.get_height() / 2,
                 f"{val:.1f}/100", va="center", color="white",
                 fontsize=11, fontweight="bold")
    ax1.set_xlim(0, 115)
    ax1.set_xlabel("Score / 100", color="#aaaaaa", fontsize=9)
    ax1.set_title("Overall Score", color="white", fontsize=12, pad=8)
    ax1.tick_params(colors="#cccccc", labelsize=9)
    ax1.spines[:].set_color("#333344")
    ax1.grid(axis="x", color="#222233", linewidth=0.5, zorder=0)
    if "v2_vs_gen" in deltas:
        ax1.text(0.98, 0.04, f"v2 leads General by +{deltas['v2_vs_gen']:.0f} pts",
                 transform=ax1.transAxes, ha="right", va="bottom",
                 color="#4fc3f7", fontsize=8, style="italic")

    # ── Right: per-dimension grouped bars ────────────────────────────────────
    ax2.set_facecolor(ax_bg)
    x = np.arange(len(dim_ids))
    width = 0.25
    for i, a in enumerate(agents):
        dim_vals = [scores.get(a, {}).get(dim_key, {}).get(did) or 0 for did in dim_ids]
        ax2.bar(x + i * width, dim_vals, width,
                label=labels[a], color=colors[a], alpha=0.85, zorder=3)
    ax2.set_xticks(x + width)
    ax2.set_xticklabels(dim_short, rotation=28, ha="right", color="#cccccc", fontsize=8)
    ax2.set_ylim(0, 5.8)
    ax2.set_ylabel("Score (1–5)", color="#aaaaaa", fontsize=9)
    ax2.set_title("Per-Dimension Breakdown", color="white", fontsize=12, pad=8)
    ax2.tick_params(colors="#cccccc", labelsize=8)
    ax2.spines[:].set_color("#333344")
    ax2.grid(axis="y", color="#222233", linewidth=0.5, zorder=0)
    ax2.axhline(y=3, color="#555566", linestyle="--", alpha=0.6, linewidth=0.8)
    ax2.legend(facecolor="#1a1a2e", edgecolor="#333344",
               labelcolor="#cccccc", fontsize=8, loc="upper right")

    eval_date = latest.get("eval_date", "")
    fig.suptitle(
        f"EDB Agent Comparison — {title_suffix}  ({eval_date})",
        color="white", fontsize=10, y=1.01,
    )
    plt.tight_layout(pad=1.5)
    return fig


def make_score_chart():
    """Cross-agent comparison chart — legacy framework (eval_history)."""
    return _comparison_chart(
        _latest_legacy_eval(),
        dim_key="dimension_scores",
        title_suffix="Legacy Evaluator",
    )


def make_legacy_summary_md():
    """Score card for the legacy eval tab."""
    latest = _latest_legacy_eval()
    if latest is None:
        return "_No eval yet — run one below._"

    scores = latest.get("scores", {})
    deltas = latest.get("deltas", {})
    date   = latest.get("eval_date", "unknown")

    def fs(t): return scores.get(t, {}).get("final_score", "—")
    def ap(t):
        s = scores.get(t, {})
        p, tot = s.get("auto_passed"), s.get("auto_total")
        return f"{p}/{tot}" if p is not None else "—"

    gap = deltas.get("v2_vs_gen")
    gap_line = (
        f"The custom v2 agent outperforms a general-purpose LLM by **+{gap:.0f} points** "
        f"on EDB's specialised rubric."
        if gap is not None else ""
    )

    return (
        f"**Latest evaluation — {date}** · legacy evaluator (20 regex checks + one-call LLM judging)\n\n"
        f"| Agent | Final score | Regex checks | Why it matters |\n"
        f"|---|:---:|:---:|---|\n"
        f"| 🥇 **v2 Custom Agent** | **{fs('v2')}/100** | {ap('v2')} | Full pipeline: live data tools, state.json streaks, EIBOR chain, sector matrix |\n"
        f"| 🥈 v1 Custom Agent | {fs('v1')}/100 | {ap('v1')} | Custom prompting + sector mapping, no cross-session memory |\n"
        f"| ❌ General Agent | {fs('general')}/100 | {ap('general')} | Off-the-shelf assistant with no EDB context, tools, or calculation templates |\n\n"
        f"{gap_line}\n\n"
        f"> **Note:** The legacy evaluator judges all 7 quality dimensions in a single LLM call "
        f"(halo effect risk). See the **AutoRubric** tab for atomic per-criterion judging."
    )

# ── Gradio UI ─────────────────────────────────────────────────────────────────
with gr.Blocks(title="EDB Macro Intelligence Agent", theme=gr.themes.Base()) as demo:
    gr.Markdown(
        "# EDB Macro Intelligence Agent\n"
        "*Emirates Development Bank — Daily Macro Brief Pipeline*"
    )

    with gr.Tabs():

        # ── Tab 1: Daily Brief ──────────────────────────────────────────────
        with gr.Tab("📋 Daily Brief"):
            with gr.Row():
                # Left: generate + log
                with gr.Column(scale=1, min_width=300):
                    run_btn = gr.Button("▶  Generate New Brief", variant="primary", size="lg")
                    gr.Markdown(
                        "*Runs the Claude Agent SDK in GitHub Actions (~3–6 min). "
                        "Click 🔄 to load the new brief when it finishes.*"
                    )
                    log_out = gr.Textbox(
                        label="Trigger status", lines=10, max_lines=20,
                        interactive=False, show_copy_button=True,
                        placeholder="Click 'Generate New Brief' to trigger a run…",
                    )

                # Right: brief viewer
                with gr.Column(scale=2):
                    with gr.Row():
                        brief_dropdown = gr.Dropdown(
                            label="Browse briefs (from GitHub)", choices=[],
                            interactive=True, scale=5,
                        )
                        refresh_btn = gr.Button("🔄", scale=0)
                    brief_out = gr.Markdown(
                        value="*Select a brief from the dropdown, or generate a new one.*"
                    )

            # Wiring: brief generation (triggers CI, then refresh the dropdown)
            run_btn.click(
                fn=run_brief, inputs=[], outputs=[log_out, brief_out], api_name=False,
            )

            # Wiring: dropdown browse
            refresh_btn.click(fn=refresh_brief_dropdown, outputs=[brief_dropdown], api_name=False)
            brief_dropdown.change(
                fn=load_brief, inputs=[brief_dropdown], outputs=[brief_out], api_name=False,
            )

            # On load: populate dropdown
            demo.load(fn=refresh_brief_dropdown, outputs=[brief_dropdown], api_name=False)

        # ── Tab 2: Evaluation (legacy framework) ────────────────────────────
        with gr.Tab("📊 Agent Comparison (Legacy Eval)"):
            gr.Markdown(
                "*Note: judging all 7 dimensions in a single call risks halo effect — "
                "a polished brief may receive uniformly high marks. The AutoRubric tab fixes this.*"
            )

            score_plot   = gr.Plot(label="Agent comparison")
            legacy_summary = gr.Markdown(value="_Loading…_")

            with gr.Accordion("▶  Run a new evaluation", open=False):
                gr.Markdown(
                    "Triggers the Legacy evaluation in GitHub Actions (20 regex checks + one "
                    "LLM call scoring all 7 dimensions), which commits the report. ~1–2 min; "
                    "click 🔄 to refresh when done."
                )
                eval_btn = gr.Button("Run Legacy Eval", variant="primary")
                eval_log = gr.Textbox(
                    label="Eval log", lines=10, max_lines=20,
                    interactive=False, show_copy_button=True,
                )

            with gr.Accordion("📄 Full eval report", open=False):
                with gr.Row():
                    eval_dropdown = gr.Dropdown(
                        label="Select report", choices=[],
                        interactive=True, scale=5,
                    )
                    refresh_eval_btn = gr.Button("🔄", scale=0)
                eval_out = gr.Markdown(value="*Select a report above.*")

            # Wiring: eval
            eval_btn.click(fn=run_eval, outputs=[eval_log, eval_out], api_name=False).then(
                fn=refresh_eval_dropdown, outputs=[eval_dropdown], api_name=False,
            ).then(
                fn=make_score_chart, outputs=[score_plot], api_name=False,
            ).then(
                fn=make_legacy_summary_md, outputs=[legacy_summary], api_name=False,
            )
            refresh_eval_btn.click(fn=refresh_eval_dropdown, outputs=[eval_dropdown], api_name=False)
            eval_dropdown.change(fn=load_eval, inputs=[eval_dropdown], outputs=[eval_out], api_name=False)

            # On load: populate eval dropdown + chart + summary
            demo.load(fn=refresh_eval_dropdown, outputs=[eval_dropdown], api_name=False)
            demo.load(fn=make_score_chart, outputs=[score_plot], api_name=False)
            demo.load(fn=make_legacy_summary_md, outputs=[legacy_summary], api_name=False)

        # ── Tab 3: AutoRubric — Agent Comparison ────────────────────────────
        with gr.Tab("🧪 Agent Comparison (AutoRubric)"):
            gr.Markdown(
                "Framework: [AutoRubric](https://autorubric.org) — "
                "analytic rubric, each criterion judged in its own LLM call (no halo effect). "
                "10 binary structural criteria + 7 ordinal quality dimensions + 3 negative "
                "penalties. 2-model ensemble: Claude Haiku + Gemini Flash, majority vote."
            )

            ar_plot    = gr.Plot(label="Agent comparison")
            ar_summary = gr.Markdown(value="_Loading…_")

            with gr.Accordion("▶  Run a new evaluation", open=False):
                gr.Markdown(
                    "Triggers the AutoRubric evaluation in GitHub Actions — grades every "
                    "criterion atomically with the 2-model ensemble, commits the report, and "
                    "updates state.json. ~2–3 min; click 🔄 to refresh when done."
                )
                ar_btn = gr.Button("Run AutoRubric Eval", variant="primary")
                ar_log = gr.Textbox(
                    label="Run log", lines=10, max_lines=20,
                    interactive=False, show_copy_button=True,
                )

            with gr.Accordion("📄 Full eval report", open=False):
                with gr.Row():
                    ar_dropdown = gr.Dropdown(
                        label="Select report", choices=[],
                        interactive=True, scale=5,
                    )
                    ar_refresh_btn = gr.Button("🔄", scale=0)
                ar_out = gr.Markdown(value="*Select a report above.*")

            # Wiring
            ar_btn.click(
                fn=run_autorubric_eval, outputs=[ar_log, ar_out], api_name=False,
            ).then(
                fn=refresh_autorubric_dropdown, outputs=[ar_dropdown], api_name=False,
            ).then(
                fn=make_autorubric_comparison_chart, outputs=[ar_plot], api_name=False,
            ).then(
                fn=make_autorubric_summary_md, outputs=[ar_summary], api_name=False,
            )
            ar_refresh_btn.click(
                fn=refresh_autorubric_dropdown, outputs=[ar_dropdown], api_name=False,
            )
            ar_dropdown.change(
                fn=load_autorubric_eval, inputs=[ar_dropdown], outputs=[ar_out], api_name=False,
            )

            demo.load(fn=refresh_autorubric_dropdown, outputs=[ar_dropdown], api_name=False)
            demo.load(fn=make_autorubric_comparison_chart, outputs=[ar_plot], api_name=False)
            demo.load(fn=make_autorubric_summary_md, outputs=[ar_summary], api_name=False)

if __name__ == "__main__":
    demo.launch()
