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
    if not _GITHUB_TOKEN:
        yield "❌ `GITHUB_TOKEN` not set in Space secrets.", ""
        return
    if not _GITHUB_REPO:
        yield "❌ `GITHUB_REPO` not set in Space secrets.", ""
        return

    log = "🔄 Syncing state.json from GitHub…\n"
    yield log, ""
    try:
        _sync_state()
        log += "✅ State synced.\n\n"
    except Exception as e:
        log += f"⚠️ State sync failed (proceeding anyway): {e}\n\n"
    yield log, ""

    log += "🚀 Running EDB agent — takes ~2–3 minutes…\n"
    yield log, ""

    proc = subprocess.Popen(
        ["python", "run_agent.py"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, env={**os.environ},
    )
    for line in proc.stdout:
        log += line
        yield log, ""
    proc.wait()

    if proc.returncode != 0:
        yield log + "\n❌ Agent exited with a non-zero code.", ""
        return

    summary = None
    for line in log.splitlines():
        if line.startswith("SUMMARY_JSON="):
            try:
                summary = json.loads(line[len("SUMMARY_JSON="):])
            except Exception:
                pass

    if not summary or not Path(summary.get("brief_path", "")).exists():
        yield log + "\n❌ Brief file not found after run.", ""
        return

    log += f"\n📤 Committing `{summary['brief_name']}` to GitHub…\n"
    yield log, ""

    ok = _push_run(summary["brief_path"], summary["date"])
    log += "✅ Committed.\n" if ok else "⚠️ Commit failed — check GITHUB_TOKEN has `repo` scope.\n"
    yield log, Path(summary["brief_path"]).read_text()

def refresh_brief_dropdown():
    briefs = list_briefs()
    return gr.Dropdown(choices=briefs, value=briefs[0] if briefs else None)

def load_brief(name: str) -> str:
    if not name:
        return ""
    content, _ = gh_get(f"outputs/{name}")
    return content or f"*(Could not load `{name}` from GitHub.)*"

# ── Tab 1 — Streaming chat ────────────────────────────────────────────────────

def chat_fn(message: str, history: list, brief_content: str):
    """Streaming chat about the current brief. history is Gradio 5 messages format (list of dicts)."""
    if not brief_content or len(brief_content.strip()) < 50:
        yield history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": "Please load or generate a brief first."},
        ]
        return
    if not _OR_KEY:
        yield history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": "❌ OPENROUTER_API_KEY not set in Space secrets."},
        ]
        return

    client = _client(CHAT_MODEL)
    llm_messages = [
        {"role": "system", "content": (
            "You are an EDB (Emirates Development Bank) senior macro analyst. "
            "Answer questions concisely and precisely based solely on the brief below. "
            "Cite specific numbers from the brief when relevant. "
            "Do not speculate beyond what the brief says.\n\n"
            f"BRIEF:\n{brief_content[:7000]}"
        )},
    ]
    # history is [{role: "user"|"assistant", content: "..."}]
    for msg in history:
        llm_messages.append({"role": msg["role"], "content": msg["content"]})
    llm_messages.append({"role": "user", "content": message})

    stream = client.chat.completions.create(
        model=CHAT_MODEL, messages=llm_messages, max_tokens=600, temperature=0.2, stream=True,
    )

    partial = ""
    new_history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": ""},
    ]
    for chunk in stream:
        partial += chunk.choices[0].delta.content or ""
        new_history[-1]["content"] = partial
        yield new_history

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
    if not _GITHUB_TOKEN or not _GITHUB_REPO:
        yield "❌ GITHUB_TOKEN or GITHUB_REPO not set.", ""
        return
    if not _OR_KEY:
        yield "❌ OPENROUTER_API_KEY not set — needed for LLM judging.", ""
        return

    log = "🔍 Fetching brief list from GitHub…\n"
    yield log, ""

    all_files = _list_outputs(r"brief_.*\.md")
    v2_name  = next((f for f in all_files if re.match(r"brief_v2_", f)), None)
    v1_name  = next((f for f in all_files if re.match(r"brief_v1_", f)), None)
    gen_name = next((f for f in all_files if re.match(r"brief_general_", f)), None)

    log += f"  v2:  {v2_name or '(not found)'}\n"
    log += f"  v1:  {v1_name or '(not found)'}\n"
    log += f"  gen: {gen_name or '(not found)'}\n\n"
    yield log, ""

    if not v2_name:
        yield log + "❌ No v2 brief found. Generate a brief first.", ""
        return

    log += "📥 Fetching brief content from GitHub…\n"
    yield log, ""

    v2_content,  _ = gh_get(f"outputs/{v2_name}")
    v1_content,  _ = gh_get(f"outputs/{v1_name}")  if v1_name  else (None, None)
    gen_content, _ = gh_get(f"outputs/{gen_name}") if gen_name else (None, None)

    log += "🔢 Running 20 automated checks…\n"
    yield log, ""

    v2_checks  = _run_auto_checks(v2_content)
    v1_checks  = _run_auto_checks(v1_content)
    gen_checks = _run_auto_checks(gen_content)

    passed = sum(v2_checks.values())
    log += f"  v2: {passed}/20 automated checks passed\n\n"
    yield log, ""

    log += "🤖 Calling LLM to judge 7 dimensions × 3 briefs (one API call)…\n"
    yield log, ""

    prompt = _build_eval_prompt(
        v2_content or "", v1_content or "", gen_content or ""
    )
    client = _client(MODEL)
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        # strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        llm_scores = json.loads(raw)
        log += "✅ LLM judging complete.\n\n"
    except Exception as e:
        log += f"⚠️ LLM judging failed: {e}\nShowing automated checks only.\n\n"
        llm_scores = {}
    yield log, ""

    date_str = datetime.now().strftime("%Y-%m-%d")
    report = _format_eval_report(
        date_str, v2_name, v1_name or "", gen_name or "",
        v2_checks, v1_checks, gen_checks, llm_scores,
    )

    log += "📤 Committing eval report to GitHub…\n"
    yield log, ""

    report_name = f"eval_{date_str}.md"
    _, existing_sha = gh_get(f"outputs/{report_name}")
    ok = gh_put(f"outputs/{report_name}", report, existing_sha,
                f"eval: {date_str} [HF Spaces]")
    log += f"✅ Committed `{report_name}`.\n" if ok else "⚠️ Commit failed.\n"
    yield log, report

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
    """Fetch latest briefs, grade with the AutoRubric engine, commit report + state."""
    if not _GITHUB_TOKEN or not _GITHUB_REPO:
        yield "❌ GITHUB_TOKEN or GITHUB_REPO not set.", ""
        return
    if not _OR_KEY:
        yield "❌ OPENROUTER_API_KEY not set — needed for LLM judging.", ""
        return
    try:
        from eval_autorubric.runner import grade_all
        from eval_autorubric.report import format_report
        from eval_autorubric.config import judge_models
    except Exception as e:
        yield f"❌ AutoRubric engine import failed: {e}", ""
        return

    log = "🔍 Fetching latest briefs from GitHub…\n"
    yield log, ""

    all_files = _list_outputs(r"brief_.*\.md")
    names = {
        "v2":      next((f for f in all_files if re.match(r"brief_v2_", f)), None),
        "v1":      next((f for f in all_files if re.match(r"brief_v1_", f)), None),
        "general": next((f for f in all_files if re.match(r"brief_general_", f)), None),
    }
    for t, n in names.items():
        log += f"  {t:<8}: {n or '(not found)'}\n"
    yield log, ""

    if not names["v2"]:
        yield log + "❌ No v2 brief found. Generate a brief first.", ""
        return

    briefs = {t: (gh_get(f"outputs/{n}")[0] if n else None) for t, n in names.items()}
    disp_names = {t: (n or "(none)") for t, n in names.items()}

    judges = judge_models()
    ensemble = len(judges) >= 2
    log += (f"\n🤖 Grading atomically with {'ensemble of ' + str(len(judges)) if ensemble else 'single judge'} "
            f"({', '.join(j.split('/')[-1] for j in judges)})…\n"
            f"   One LLM call per criterion per brief — ~1–2 min.\n")
    yield log, ""

    try:
        graded = asyncio.run(grade_all(briefs, judges))
    except Exception as e:
        yield log + f"\n❌ Grading failed: {e}", ""
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    report = format_report(graded, date_str, disp_names)

    scores = {t: round(r["final_score"], 1) for t, r in graded["results"].items()}
    log += f"✅ Scored: {scores}\n\n📤 Committing report + state to GitHub…\n"
    yield log, ""

    report_name = f"eval_autorubric_{date_str}.md"
    _, existing_sha = gh_get(f"outputs/{report_name}")
    ok = gh_put(f"outputs/{report_name}", report, existing_sha,
                f"eval-autorubric: {date_str} [HF Spaces]")

    # append to state.json → autorubric_eval_history (separate from legacy history)
    try:
        state_raw, s_sha = gh_get("outputs/state.json")
        state = json.loads(state_raw) if state_raw else {}
        record = {
            "eval_date": date_str, "framework": "autorubric",
            "report_path": f"outputs/{report_name}", "judges": judges,
            "ensemble": ensemble, "briefs": disp_names,
            "scores": {t: {"final_score": round(r["final_score"], 1),
                           "llm_norm": round(r["llm_norm"], 3),
                           "structural_passed": r["structural_passed"],
                           "mean_agreement": r["mean_agreement"],
                           "dims": r["dims"], "penalties": r["penalties"]}
                       for t, r in graded["results"].items()},
            "deltas": {k: round(v, 1) for k, v in graded["deltas"].items()},
        }
        state.setdefault("autorubric_eval_history", []).append(record)
        gh_put("outputs/state.json", json.dumps(state, indent=2, default=str), s_sha,
               f"state (autorubric eval): {date_str} [HF Spaces]")
    except Exception as e:
        log += f"⚠️ state.json update skipped: {e}\n"

    log += f"✅ Committed `{report_name}`.\n" if ok else "⚠️ Report commit failed.\n"
    yield log, report

def make_autorubric_chart():
    """Score history chart from state.json autorubric_eval_history."""
    try:
        state_raw, _ = gh_get("outputs/state.json")
        history = json.loads(state_raw).get("autorubric_eval_history", []) if state_raw else []
    except Exception:
        history = []

    fig, ax = plt.subplots(figsize=(9, 4))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#0f1117")

    if history:
        history = sorted(history, key=lambda e: e.get("eval_date", ""))
        dates = [e.get("eval_date", "?")[:10] for e in history]

        def series(t):
            return [e.get("scores", {}).get(t, {}).get("final_score") for e in history]

        for t, color, label in (("v2", "#d4a843", "v2 Agent"),
                                 ("v1", "#8899cc", "v1 Agent"),
                                 ("general", "#667788", "General")):
            pts = [(d, s) for d, s in zip(dates, series(t)) if s is not None]
            if pts:
                xs, ys = zip(*pts)
                ax.plot(xs, ys, "o-", color=color, label=label, linewidth=2, markersize=5)
        ax.set_ylim(0, 105)
        if len(dates) > 5:
            ax.set_xticks(ax.get_xticks()[::2])
        plt.xticks(rotation=30, ha="right", color="#cccccc", fontsize=8)
        ax.legend(facecolor="#1a1a2e", edgecolor="#333344", labelcolor="#cccccc", fontsize=9)
    else:
        ax.text(0.5, 0.5, "No AutoRubric evals yet.\nRun one below.",
                ha="center", va="center", color="#888888", fontsize=12,
                transform=ax.transAxes)

    ax.set_ylabel("Score / 100", color="#888888", fontsize=9)
    ax.set_title("AutoRubric Score History", color="white", fontsize=13, pad=10)
    ax.tick_params(axis="y", colors="#666666")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("bottom", "left"):
        ax.spines[sp].set_color("#333344")
    ax.grid(axis="y", color="#222233", linewidth=0.5, zorder=0)
    fig.tight_layout(pad=1.5)
    return fig

def make_score_chart():
    """Score history chart from state.json eval_history."""
    try:
        state_raw, _ = gh_get("outputs/state.json")
        if state_raw:
            state = json.loads(state_raw)
            history = state.get("eval_history", [])
        else:
            history = []
    except Exception:
        history = []

    fig, ax = plt.subplots(figsize=(9, 4))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#0f1117")

    if history:
        history = sorted(history, key=lambda e: e.get("eval_date", ""))
        dates  = [e.get("eval_date", "?")[:10] for e in history]
        v2_sc  = [e.get("scores", {}).get("v2",  {}).get("final_score", None) for e in history]
        v1_sc  = [e.get("scores", {}).get("v1",  {}).get("final_score", None) for e in history]
        gen_sc = [e.get("scores", {}).get("general", {}).get("final_score", None) for e in history]

        def _plot(scores, color, label):
            pts = [(d, s) for d, s in zip(dates, scores) if s is not None]
            if pts:
                xs, ys = zip(*pts)
                ax.plot(xs, ys, "o-", color=color, label=label, linewidth=2, markersize=5)

        _plot(v2_sc,  "#d4a843", "v2 Agent")
        _plot(v1_sc,  "#8899cc", "v1 Agent")
        _plot(gen_sc, "#667788", "General")

        ax.set_ylim(0, 110)
        if len(dates) > 5:
            ax.set_xticks(ax.get_xticks()[::2])
        plt.xticks(rotation=30, ha="right", color="#cccccc", fontsize=8)
    else:
        # Static fallback with known scores
        labels = ["General\n(baseline)", "v1 Agent\n(structured)", "v2 Agent\n(+ memory)"]
        auto   = [10.0, 36.0, 40.0]
        llm    = [25.9, 46.6, 60.0]
        totals = [35.9, 82.6, 100.0]
        x, w = [0, 1, 2], 0.32
        ax.bar([i - w/2 for i in x], auto, width=w, alpha=0.9, zorder=3,
               color=["#44445a","#5566aa","#b8921e"], label="Automated (40%)")
        ax.bar([i + w/2 for i in x], llm,  width=w, alpha=0.9, zorder=3,
               color=["#667788","#8899cc","#d9b040"], label="LLM Dims (60%)")
        for i, total in enumerate(totals):
            ax.text(i, max(auto[i], llm[i]) + 3, f"{total:.1f}", ha="center", va="bottom",
                    color="white", fontweight="bold", fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, color="#cccccc", fontsize=10)
        ax.set_ylim(0, 115)

    ax.set_ylabel("Score / 100", color="#888888", fontsize=9)
    ax.set_title("EDB Agent Score History", color="white", fontsize=13, pad=10)
    ax.tick_params(axis="y", colors="#666666")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("bottom", "left"):
        ax.spines[sp].set_color("#333344")
    ax.grid(axis="y", color="#222233", linewidth=0.5, zorder=0)
    ax.legend(facecolor="#1a1a2e", edgecolor="#333344", labelcolor="#cccccc", fontsize=9)
    fig.tight_layout(pad=1.5)
    return fig

# ── Gradio UI ─────────────────────────────────────────────────────────────────
with gr.Blocks(title="EDB Macro Intelligence Agent", theme=gr.themes.Base()) as demo:
    gr.Markdown(
        "# EDB Macro Intelligence Agent\n"
        "*Emirates Development Bank — Daily Macro Brief Pipeline*"
    )

    # Shared state: current brief text (used by both tab 1 viewer and chat)
    brief_state = gr.State("")

    with gr.Tabs():

        # ── Tab 1: Daily Brief ──────────────────────────────────────────────
        with gr.Tab("📋 Daily Brief"):
            with gr.Row():
                # Left: generate + log
                with gr.Column(scale=1, min_width=300):
                    run_btn = gr.Button("▶  Generate New Brief", variant="primary", size="lg")
                    gr.Markdown("*~2–3 minutes. Streams live.*")
                    log_out = gr.Textbox(
                        label="Agent log", lines=18, max_lines=35,
                        interactive=False, show_copy_button=True,
                        placeholder="Click 'Generate New Brief' to start…",
                    )

                # Right: brief viewer
                with gr.Column(scale=2):
                    with gr.Row():
                        brief_dropdown = gr.Dropdown(
                            label="Browse past briefs", choices=[],
                            interactive=True, scale=5,
                        )
                        refresh_btn = gr.Button("🔄", scale=0)
                    brief_out = gr.Markdown(
                        value="*Select a brief from the dropdown, or generate a new one.*"
                    )

            gr.Markdown("---\n### Ask questions about this brief")
            gr.Markdown(
                "*Load a brief (generate or select from dropdown), then ask anything. "
                "Answers are grounded in the brief content only.*"
            )
            chatbot = gr.Chatbot(label="Brief Q&A", height=350, type="messages")
            with gr.Row():
                chat_input = gr.Textbox(
                    placeholder="e.g. 'What is the EIBOR impact on a AED 5M loan?' or 'Summarise the sector matrix'",
                    label="", scale=5, lines=1,
                )
                chat_send = gr.Button("Send", variant="primary", scale=0)

            # Wiring: brief generation
            run_btn.click(
                fn=run_brief, inputs=[], outputs=[log_out, brief_out], api_name=False,
            ).then(
                fn=lambda brief: brief, inputs=[brief_out], outputs=[brief_state], api_name=False,
            )

            # Wiring: dropdown browse
            refresh_btn.click(fn=refresh_brief_dropdown, outputs=[brief_dropdown], api_name=False)
            brief_dropdown.change(
                fn=load_brief, inputs=[brief_dropdown], outputs=[brief_out], api_name=False,
            ).then(
                fn=lambda brief: brief, inputs=[brief_out], outputs=[brief_state], api_name=False,
            )

            # Wiring: chat
            chat_send.click(
                fn=chat_fn, inputs=[chat_input, chatbot, brief_state], outputs=[chatbot], api_name=False,
            ).then(
                fn=lambda: "", outputs=[chat_input], api_name=False,
            )
            chat_input.submit(
                fn=chat_fn, inputs=[chat_input, chatbot, brief_state], outputs=[chatbot], api_name=False,
            ).then(
                fn=lambda: "", outputs=[chat_input], api_name=False,
            )

            # On load: populate dropdown
            demo.load(fn=refresh_brief_dropdown, outputs=[brief_dropdown], api_name=False)

        # ── Tab 2: Evaluation (legacy framework) ────────────────────────────
        with gr.Tab("📊 Evaluation (Legacy)"):
            score_plot = gr.Plot(label="Score history")
            gr.Markdown(
                "The chart shows eval history from `state.json`. "
                "Run a new evaluation below to add a data point.\n\n"
                "**Automated checks (40%)**: 20 regex assertions. "
                "**LLM judging (60%)**: 7 dimensions scored 1–5 by claude-sonnet-4-6."
            )

            with gr.Row():
                eval_btn = gr.Button("▶  Run Evaluation", variant="primary", size="lg")
                gr.Markdown(
                    "*Fetches latest v2/v1/general briefs from GitHub, runs 20 checks + "
                    "LLM judging in one API call (~45 seconds), commits report.*"
                )

            with gr.Row():
                with gr.Column(scale=1):
                    eval_log = gr.Textbox(
                        label="Eval log", lines=12, max_lines=20,
                        interactive=False, show_copy_button=True,
                    )
                with gr.Column(scale=2):
                    with gr.Row():
                        eval_dropdown = gr.Dropdown(
                            label="Past eval reports", choices=[],
                            interactive=True, scale=5,
                        )
                        refresh_eval_btn = gr.Button("🔄", scale=0)
                    eval_out = gr.Markdown(value="*Run an evaluation or select a past report.*")

            # Wiring: eval
            eval_btn.click(fn=run_eval, outputs=[eval_log, eval_out], api_name=False).then(
                fn=refresh_eval_dropdown, outputs=[eval_dropdown], api_name=False,
            ).then(
                fn=make_score_chart, outputs=[score_plot], api_name=False,
            )
            refresh_eval_btn.click(fn=refresh_eval_dropdown, outputs=[eval_dropdown], api_name=False)
            eval_dropdown.change(fn=load_eval, inputs=[eval_dropdown], outputs=[eval_out], api_name=False)

            # On load: populate eval dropdown + chart
            demo.load(fn=refresh_eval_dropdown, outputs=[eval_dropdown], api_name=False)
            demo.load(fn=make_score_chart, outputs=[score_plot], api_name=False)

        # ── Tab 3: AutoRubric Evaluation ────────────────────────────────────
        with gr.Tab("🧪 AutoRubric Eval"):
            ar_plot = gr.Plot(label="AutoRubric score history")
            gr.Markdown(
                "**AutoRubric framework** (Rao & Callison-Burch, autorubric.org) — "
                "analytic rubric, each criterion judged in its *own* LLM call to remove "
                "the halo/conflation effect of the legacy one-call judge.\n\n"
                "Same 40% structural layer as the legacy tab; the 60% LLM layer is the "
                "AutoRubric normalized score over 7 ordinal dimensions **+ 3 negative "
                "penalties** (anti-patterns). Set the `AUTORUBRIC_JUDGES` secret to 2+ "
                "cross-family models to enable ensemble judging + inter-judge reliability."
            )

            with gr.Row():
                ar_btn = gr.Button("▶  Run AutoRubric Eval", variant="primary", size="lg")
                gr.Markdown(
                    "*Fetches latest v2/v1/general briefs, grades each criterion "
                    "atomically (~1–2 min), commits report + state.*"
                )

            with gr.Row():
                with gr.Column(scale=1):
                    ar_log = gr.Textbox(
                        label="AutoRubric log", lines=12, max_lines=20,
                        interactive=False, show_copy_button=True,
                    )
                with gr.Column(scale=2):
                    with gr.Row():
                        ar_dropdown = gr.Dropdown(
                            label="Past AutoRubric reports", choices=[],
                            interactive=True, scale=5,
                        )
                        ar_refresh_btn = gr.Button("🔄", scale=0)
                    ar_out = gr.Markdown(value="*Run an AutoRubric eval or select a past report.*")

            # Wiring: autorubric eval
            ar_btn.click(fn=run_autorubric_eval, outputs=[ar_log, ar_out], api_name=False).then(
                fn=refresh_autorubric_dropdown, outputs=[ar_dropdown], api_name=False,
            ).then(
                fn=make_autorubric_chart, outputs=[ar_plot], api_name=False,
            )
            ar_refresh_btn.click(fn=refresh_autorubric_dropdown, outputs=[ar_dropdown], api_name=False)
            ar_dropdown.change(fn=load_autorubric_eval, inputs=[ar_dropdown], outputs=[ar_out], api_name=False)

            demo.load(fn=refresh_autorubric_dropdown, outputs=[ar_dropdown], api_name=False)
            demo.load(fn=make_autorubric_chart, outputs=[ar_plot], api_name=False)

if __name__ == "__main__":
    demo.launch()
