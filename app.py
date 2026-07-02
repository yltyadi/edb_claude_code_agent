#!/usr/bin/env python3
"""
EDB Macro Intelligence — HuggingFace Spaces frontend.

Two tabs:
  Tab 1 — Daily Brief: generate a new brief (streaming), browse past briefs
  Tab 2 — Improvement Story: score chart + why v2 beats a general agent

Required HF Space secrets:
  OPENROUTER_API_KEY  — OpenRouter key for the LLM call
  FRED_API_KEY        — FRED API key for economic data
  GITHUB_TOKEN        — Personal access token with repo write access
  GITHUB_REPO         — e.g. "yltyadi/edb-macro-agent-v2"
"""

import base64
import json
import os
import re
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests

# Gradio 4–5 early versions import HfFolder which was removed from huggingface_hub 0.26+.
# We don't use HF OAuth (secrets come from Space env vars), so a no-op stub is sufficient.
try:
    from huggingface_hub import HfFolder  # noqa: F401 — already present, nothing to do
except ImportError:
    import huggingface_hub as _hf
    import types as _types
    _hf.HfFolder = _types.SimpleNamespace(  # type: ignore[attr-defined]
        get_token=lambda: None,
        save_token=lambda token: None,
        delete_token=lambda: None,
    )

import gradio as gr

# ── GitHub API ────────────────────────────────────────────────────────────────
_GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
_GITHUB_REPO  = os.environ.get("GITHUB_REPO", "")   # e.g. "yltyadi/edb-macro-agent-v2"
_GH_BASE      = "https://api.github.com"


def _gh_headers() -> dict:
    return {"Authorization": f"token {_GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}


def gh_get(path: str) -> tuple:
    """Fetch a file from the repo. Returns (content_str, sha) or (None, None)."""
    r = requests.get(f"{_GH_BASE}/repos/{_GITHUB_REPO}/contents/{path}",
                     headers=_gh_headers(), timeout=20)
    if r.ok:
        d = r.json()
        return base64.b64decode(d["content"]).decode(), d["sha"]
    return None, None


def gh_put(path: str, content: str, sha, message: str) -> bool:
    """Create or update a file in the repo."""
    payload = {"message": message,
                "content": base64.b64encode(content.encode()).decode()}
    if sha:
        payload["sha"] = sha
    r = requests.put(f"{_GH_BASE}/repos/{_GITHUB_REPO}/contents/{path}",
                     headers={**_gh_headers(), "Content-Type": "application/json"},
                     json=payload, timeout=20)
    return r.status_code in (200, 201)


def list_briefs() -> list:
    """Return brief filenames sorted newest-first."""
    r = requests.get(f"{_GH_BASE}/repos/{_GITHUB_REPO}/contents/outputs",
                     headers=_gh_headers(), timeout=15)
    if not r.ok:
        return []
    pat = re.compile(r"brief_v\d+_\d{4}-\d{2}-\d{2}_\d{4}\.md")
    names = [f["name"] for f in r.json()
             if isinstance(f, dict) and pat.match(f.get("name", ""))]
    return sorted(names, reverse=True)


# ── State sync ────────────────────────────────────────────────────────────────

def _sync_state_from_github() -> None:
    """Pull latest state.json from GitHub to local disk before each run."""
    content, _ = gh_get("outputs/state.json")
    if content:
        Path("outputs").mkdir(exist_ok=True)
        Path("outputs/state.json").write_text(content)


def _push_run_to_github(brief_path: str, date: str) -> bool:
    """Commit the generated brief + updated state.json back to GitHub."""
    ok = True
    # Brief
    brief_text = Path(brief_path).read_text()
    _, brief_sha = gh_get(brief_path)
    ok = gh_put(brief_path, brief_text, brief_sha, f"brief: {date} [HF Spaces]") and ok
    # State
    state_p = Path("outputs/state.json")
    if state_p.exists():
        _, state_sha = gh_get("outputs/state.json")
        ok = gh_put("outputs/state.json", state_p.read_text(), state_sha,
                    f"state: {date} [HF Spaces]") and ok
    return ok


# ── Tab 1: Run brief ──────────────────────────────────────────────────────────

def run_brief():
    """Generator — streams agent log lines then yields the final brief markdown."""
    if not _GITHUB_TOKEN:
        yield "❌ `GITHUB_TOKEN` secret is not set.\nAdd it under Space → Settings → Variables and secrets.", ""
        return
    if not _GITHUB_REPO:
        yield "❌ `GITHUB_REPO` secret is not set (e.g. `yltyadi/edb-macro-agent-v2`).", ""
        return

    log = "🔄 Syncing state.json from GitHub…\n"
    yield log, ""
    try:
        _sync_state_from_github()
        log += "✅ State synced.\n\n"
    except Exception as exc:
        log += f"⚠️ State sync failed (proceeding anyway): {exc}\n\n"
    yield log, ""

    log += "🚀 Running EDB agent — takes 2–3 minutes…\n"
    yield log, ""

    proc = subprocess.Popen(
        ["python", "run_agent.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={**os.environ},
    )
    for line in proc.stdout:
        log += line
        yield log, ""
    proc.wait()

    if proc.returncode != 0:
        yield log + "\n❌ Agent exited with a non-zero code. Check the log above.", ""
        return

    summary = None
    for line in log.splitlines():
        if line.startswith("SUMMARY_JSON="):
            try:
                summary = json.loads(line[len("SUMMARY_JSON="):])
            except Exception:
                pass

    if not summary:
        yield log + "\n❌ SUMMARY_JSON not found in output — brief may not have been written.", ""
        return
    if not Path(summary.get("brief_path", "")).exists():
        yield log + f"\n❌ Expected brief file `{summary.get('brief_path')}` not on disk.", ""
        return

    log += f"\n📤 Committing `{summary['brief_name']}` to GitHub…\n"
    yield log, ""

    ok = _push_run_to_github(summary["brief_path"], summary["date"])
    if ok:
        log += "✅ Committed to GitHub successfully.\n"
    else:
        log += "⚠️ Brief generated locally but GitHub commit failed — verify GITHUB_TOKEN has `repo` write scope.\n"

    brief_content = Path(summary["brief_path"]).read_text()
    yield log, brief_content


def refresh_dropdown():
    briefs = list_briefs()
    return gr.Dropdown(choices=briefs, value=briefs[0] if briefs else None)


def load_brief_from_github(name: str) -> str:
    if not name:
        return ""
    content, _ = gh_get(f"outputs/{name}")
    return content or f"*(Could not load `{name}` from GitHub.)*"


# ── Tab 2: Improvement story ──────────────────────────────────────────────────

def make_score_chart():
    """Return a dark-themed bar chart comparing General / v1 / v2 scores."""
    labels = ["General\n(baseline)", "v1 Agent\n(structured)", "v2 Agent\n(+ memory)"]
    auto   = [10.0, 36.0, 40.0]
    llm    = [25.9, 46.6, 60.0]
    totals = [35.9, 82.6, 100.0]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#0f1117")

    x = [0, 1, 2]
    w = 0.32

    # Auto bars (darker)
    bars_auto = ax.bar([i - w / 2 for i in x], auto, width=w, zorder=3, alpha=0.9,
                       color=["#44445a", "#5566aa", "#b8921e"], label="Automated (40%)")
    # LLM bars (lighter)
    bars_llm = ax.bar([i + w / 2 for i in x], llm, width=w, zorder=3, alpha=0.9,
                      color=["#667788", "#8899cc", "#d9b040"], label="LLM Dimensions (60%)")

    # Total annotation above each pair
    for i, total in enumerate(totals):
        y_top = max(auto[i], llm[i]) + 3
        ax.text(i, y_top, f"{total:.1f}", ha="center", va="bottom",
                color="white", fontweight="bold", fontsize=12)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, color="#cccccc", fontsize=10)
    ax.set_ylabel("Score contribution (/ 100 total)", color="#888888", fontsize=9)
    ax.set_ylim(0, 115)
    ax.set_title("EDB Agent Score Progression", color="white", fontsize=13, pad=12)
    ax.tick_params(axis="y", colors="#666666")
    ax.tick_params(axis="x", colors="#cccccc", length=0)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("bottom", "left"):
        ax.spines[spine].set_color("#333344")
    ax.grid(axis="y", color="#222233", linewidth=0.5, zorder=0)
    ax.legend(facecolor="#1a1a2e", edgecolor="#333344", labelcolor="#cccccc",
              fontsize=9, loc="upper left")

    fig.tight_layout(pad=1.5)
    return fig


STORY_MD = """
## How the EDB v2 Agent Beats a General Claude Response

EDB needs daily macro intelligence mapped to its **five priority sectors**
(Advanced Technology, Manufacturing, Healthcare, Renewables, Food Security)
with quantified AED impacts, EIBOR transmission, and credit-team action flags.
A general-purpose Claude response cannot produce any of this structurally.

---

### Score breakdown

| Agent | Automated (40%) | LLM Dimensions (60%) | **Final Score** |
|-------|:---------------:|:--------------------:|:---------------:|
| General (baseline) | 10.0 | 25.9 | **35.9 / 100** |
| v1 (EDB pipeline) | 36.0 | 46.6 | **82.6 / 100** |
| v2 (+ memory loop) | **40.0** | **60.0** | **100.0 / 100** |

*20 automated checks (binary) + 7 LLM-judged dimensions (1–5, weighted).*

---

### What each tier added

**v1 over General (+46.7 pts)** — Added structural discipline: Type A Executive Brief,
Type B Credit Alert with a live Python calculation block, Type C Stakeholder Bulletin,
5-sector impact matrix, EIBOR ADS ±25/50bps scenarios, oil fiscal AED conversion
(×3.6725 peg step shown explicitly), petrochemical pass-through (60% × AED 17.5bn feedstock),
Op300bn gap method ((current − 133) / (300 − 133)), Sources + Methodology sections.
None of this appears in a generic Claude response.

**v2 over v1 (+17.4 pts)** — Added cross-session memory via `state.json`:
- **Streak language** — "EIBOR unchanged for 201 consecutive days", "5th consecutive Fed hold"
- **Delta calculations** — today's Brent vs prior-run baseline: Δ $6.60/bbl
- **Signal classification** — `[NEW]` vs `[CONTINUING — N days]` for every signal in the brief
- **CLAUDE.md feedback loop** — any dimension scoring ≤ 3 triggers an appended improvement note;
  the next run picks it up as part of the system prompt

---

### LLM dimension scores

| Dimension | Weight | General | v1 | v2 |
|-----------|:------:|:-------:|:--:|:--:|
| Mandate Relevance      | 20% | 2/5 | 4/5 | **5/5** |
| Data Grounding         | 16% | 3/5 | 4/5 | **5/5** |
| Quantitative Accuracy  | 16% | 2/5 | 4/5 | **5/5** |
| Structure Completeness | 12% | 1/5 | 4/5 | **5/5** |
| Action Specificity     | 12% | 2/5 | 4/5 | **5/5** |
| Data Integrity         | 12% | 3/5 | 5/5 | **5/5** |
| Trend & Continuity     | 12% | 2/5 | 2/5 | **5/5** |

*Trend & Continuity is structurally capped at 2/5 without `state.json` — v2's exclusive advantage.*

---

### Why the General agent ceiling is stable at ~36

The 35.9 score holds across five different evaluation dates (zero drift).
The gaps are structural, not content quality: no EDB data tools, no state memory,
no format — so the brief fails 15 of the 20 automated checks regardless of how good
the prose is. Better prompting cannot close these gaps without the underlying pipeline.
"""


# ── Build UI ──────────────────────────────────────────────────────────────────

with gr.Blocks(title="EDB Macro Intelligence Agent", theme=gr.themes.Base()) as demo:
    gr.Markdown(
        "# EDB Macro Intelligence Agent\n"
        "*Emirates Development Bank — Daily Macro Brief Pipeline*"
    )

    with gr.Tabs():

        # ── Tab 1: Daily Brief ──────────────────────────────────────────────
        with gr.Tab("📋 Daily Brief"):
            with gr.Row():
                # Left column — controls + log
                with gr.Column(scale=1, min_width=320):
                    run_btn = gr.Button("▶  Generate New Brief", variant="primary", size="lg")
                    gr.Markdown("*Streams live output. Takes ~2–3 minutes.*")
                    log_out = gr.Textbox(
                        label="Agent log",
                        lines=20,
                        max_lines=40,
                        interactive=False,
                        placeholder="Click 'Generate New Brief' to start…",
                        show_copy_button=True,
                    )

                # Right column — brief viewer
                with gr.Column(scale=2):
                    with gr.Row():
                        brief_dropdown = gr.Dropdown(
                            label="Browse past briefs",
                            choices=[],
                            interactive=True,
                            scale=5,
                        )
                        refresh_btn = gr.Button("🔄", scale=0)

                    brief_out = gr.Markdown(
                        value="*Select a brief from the dropdown, or generate a new one.*",
                    )

            # Event wiring
            run_btn.click(
                fn=run_brief,
                inputs=[],
                outputs=[log_out, brief_out],
            )
            refresh_btn.click(
                fn=refresh_dropdown,
                inputs=[],
                outputs=[brief_dropdown],
            )
            brief_dropdown.change(
                fn=load_brief_from_github,
                inputs=[brief_dropdown],
                outputs=[brief_out],
            )

            # On load: populate dropdown
            demo.load(fn=refresh_dropdown, inputs=[], outputs=[brief_dropdown])

        # ── Tab 2: Improvement story ────────────────────────────────────────
        with gr.Tab("📈 Why v2 Beats a General Agent"):
            score_plot = gr.Plot(label="")
            gr.Markdown(STORY_MD)

            # On load: render chart
            demo.load(fn=make_score_chart, inputs=[], outputs=[score_plot])


if __name__ == "__main__":
    demo.launch()
