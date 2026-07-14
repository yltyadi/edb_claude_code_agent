#!/usr/bin/env python3
"""
AutoRubric evaluator — CLI entrypoint (used by the /eval-brief-autorubric skill).

Locates the latest v2 / v1 / general briefs in outputs/, grades all three with
the AutoRubric engine, writes a markdown report, and appends a record to
state.json under `autorubric_eval_history` (kept separate from the OLD framework's
`eval_history`, so both frameworks accumulate independently and stay comparable).

Usage:
  venv/bin/python -m eval_autorubric.run_eval
  venv/bin/python -m eval_autorubric.run_eval --v2 outputs/brief_v2_....md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from eval_autorubric.report import format_report      # noqa: E402
from eval_autorubric.runner import grade_all           # noqa: E402
from eval.rubric import LLM_DIMENSIONS                 # noqa: E402

OUTPUTS = ROOT / "outputs"
STATE_PATH = OUTPUTS / "state.json"
CLAUDE_MD = ROOT / "CLAUDE.md"

_DIM_NAME = {d["id"]: d["name"] for d in LLM_DIMENSIONS}

# Targeted fix guidance per anti-pattern, appended to CLAUDE.md when the penalty fires.
_PENALTY_FIX = {
    "unsupported_number": (
        "Every material figure (rate, price, AED amount, %) must trace to a shown calculation "
        "block or a named source. Compute each derived quantity ONCE and reuse that exact number "
        "everywhere (headline, Key number, matrix, Type B). When reporting more than one framing "
        "of a quantity, label precisely what each represents (uplift vs pre-crisis / total surplus "
        "above breakeven / single-session change) — different framings are different numbers, each "
        "needing its own labelled calc line. Never let the headline and Key number quote different "
        "AED figures for what a reader will take to be the same thing."
    ),
    "silent_stale_or_estimated_data": (
        "Tag every estimated or stale figure (especially EIBOR) with '(est.)' or a stale flag at "
        "EVERY point of use, adjacent to the number — not only once in Methodology. Every scenario "
        "line (base / +25bps / −25bps / −50bps) must carry the flag."
    ),
    "generic_market_commentary": (
        "Tie every signal explicitly to one of the five EDB priority sectors or the AED/USD peg "
        "chain. Cut any broad market colour that has no EDB/sector implication."
    ),
}


def _patch_claude_md(v2: dict, date_str: str) -> list[str]:
    """Self-improvement loop: idempotently append improvement notes to CLAUDE.md for the
    anti-patterns that fired on v2 and any genuinely-weak dimension (≤ 2/5). Each note is
    keyed by an `<!-- auto:... -->` marker so a lesson the agent already has is not re-added
    (re-recording an existing rule doesn't help). Dimensions at exactly 3/5 are skipped: on
    this rubric a glowing free-text reason often still lands on the middle 'Adequate' option
    (a scoring artifact), so 3/5 is too noisy to auto-patch — only ≤ 2 is a clear signal."""
    if not CLAUDE_MD.exists():
        return []
    md = CLAUDE_MD.read_text()
    reasons = v2.get("reasons", {}) or {}
    additions, added = [], []

    for pid, fired in (v2.get("penalties") or {}).items():
        marker = f"<!-- auto:penalty:{pid} -->"
        if not fired or marker in md:
            continue
        reason = (reasons.get(pid, "") or "").strip()[:400]
        fix = _PENALTY_FIX.get(pid, "Address the anti-pattern the judge cited.")
        additions.append(
            f"\n\n### {date_str} — {pid} (AutoRubric CI: penalty fired) {marker}\n"
            f"- **Observed:** {reason}\n- **Fix:** {fix}"
        )
        added.append(f"penalty:{pid}")

    for did, lvl in (v2.get("dims") or {}).items():
        marker = f"<!-- auto:dim:{did} -->"
        if lvl is None or lvl > 2 or marker in md:
            continue
        reason = (reasons.get(did, "") or "").strip()[:400]
        name = _DIM_NAME.get(did, did)
        additions.append(
            f"\n\n### {date_str} — {name} (AutoRubric CI: {lvl}/5) {marker}\n"
            f"- **Observed:** {reason}\n"
            f"- **Fix:** Strengthen this dimension per its behavioural anchors; a ≤2/5 is a "
            f"concrete deficiency, not a scoring artifact."
        )
        added.append(f"dim:{did}")

    if additions:
        CLAUDE_MD.write_text(md + "".join(additions) + "\n")
    return added


def _latest(pattern: str) -> Path | None:
    # Sort by filename, not mtime: brief_v{N}_YYYY-MM-DD_HHMM.md sorts chronologically by
    # name, and this is stable in CI (a fresh git checkout gives every file an equal mtime,
    # so mtime-based selection could grade an older brief).
    matches = sorted(OUTPUTS.glob(pattern), key=lambda p: p.name, reverse=True)
    return matches[0] if matches else None


def _resolve_briefs(args) -> dict[str, Path | None]:
    return {
        "v2": Path(args.v2) if args.v2 else _latest("brief_v2_*.md"),
        "v1": Path(args.v1) if args.v1 else _latest("brief_v1_*.md"),
        "general": Path(args.general) if args.general else _latest("brief_general_*.md"),
    }


def _update_state(record: dict) -> None:
    if not STATE_PATH.exists():
        return
    try:
        state = json.loads(STATE_PATH.read_text())
    except Exception:
        return
    state.setdefault("autorubric_eval_history", []).append(record)
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str))


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2"); ap.add_argument("--v1"); ap.add_argument("--general")
    ap.add_argument("--no-state", action="store_true", help="skip state.json update")
    ap.add_argument("--patch-claude-md", action="store_true",
                    help="close the self-improvement loop: append notes to CLAUDE.md for "
                         "penalties that fired on v2 and dimensions scoring ≤ 2/5 (idempotent)")
    args = ap.parse_args()

    paths = _resolve_briefs(args)
    if not paths["v2"] or not paths["v2"].exists():
        sys.exit("No v2 brief found in outputs/ — generate one first.")

    briefs = {t: (p.read_text(encoding="utf-8") if p and p.exists() else None)
              for t, p in paths.items()}
    names = {t: (p.name if p and p.exists() else "(none)") for t, p in paths.items()}

    print(f"Grading briefs with AutoRubric:", flush=True)
    for t, p in paths.items():
        print(f"  {t:<8}: {p.name if p and p.exists() else '(not found)'}", flush=True)

    graded = await grade_all(briefs)

    date_str = datetime.now().strftime("%Y-%m-%d")
    report = format_report(graded, date_str, names)

    report_name = f"eval_autorubric_{date_str}.md"
    report_path = OUTPUTS / report_name
    if report_path.exists():
        report_name = f"eval_autorubric_{date_str}_{datetime.now().strftime('%H%M')}.md"
        report_path = OUTPUTS / report_name
    report_path.write_text(report)

    results = graded["results"]
    record = {
        "eval_date": date_str,
        "framework": "autorubric",
        "report_path": str(report_path.relative_to(ROOT)),
        "judges": graded["judges"],
        "ensemble": graded["ensemble"],
        "briefs": names,
        "scores": {t: {"final_score": round(r["final_score"], 1),
                       "llm_score": round(r["llm_score"], 3),
                       "mean_agreement": r["mean_agreement"],
                       "binary": r["binary"],
                       "dims": r["dims"],
                       "penalties": r["penalties"]}
                   for t, r in results.items()},
        "deltas": {k: round(v, 1) for k, v in graded["deltas"].items()},
    }
    if not args.no_state:
        _update_state(record)

    if args.patch_claude_md and "v2" in results:
        added = _patch_claude_md(results["v2"], date_str)
        if added:
            print(f"CLAUDE.md self-improvement: added notes for {', '.join(added)}", flush=True)
        else:
            print("CLAUDE.md self-improvement: no new lessons (clean run or already recorded)", flush=True)

    print(f"\nReport written: {report_path.relative_to(ROOT)}", flush=True)
    for t, r in results.items():
        binary_pass = sum(1 for v in r["binary"].values() if v)
        print(f"  {t:<8}: {r['final_score']:.1f}/100  "
              f"(llm {r['llm_score']:.3f}, binary {binary_pass}/{len(r['binary'])})", flush=True)
    # machine-readable summary line for the skill to parse
    print("SUMMARY_JSON=" + json.dumps({
        "report_path": str(report_path.relative_to(ROOT)),
        "report_name": report_name,
        "date": date_str,
        "scores": {t: round(r["final_score"], 1) for t, r in results.items()},
        "deltas": {k: round(v, 1) for k, v in graded["deltas"].items()},
    }), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
