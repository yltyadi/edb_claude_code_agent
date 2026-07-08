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

OUTPUTS = ROOT / "outputs"
STATE_PATH = OUTPUTS / "state.json"


def _latest(pattern: str) -> Path | None:
    matches = sorted(OUTPUTS.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
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
                       "llm_norm": round(r["llm_norm"], 3),
                       "structural_passed": r["structural_passed"],
                       "mean_agreement": r["mean_agreement"],
                       "dims": r["dims"], "penalties": r["penalties"]}
                   for t, r in results.items()},
        "deltas": {k: round(v, 1) for k, v in graded["deltas"].items()},
    }
    if not args.no_state:
        _update_state(record)

    print(f"\nReport written: {report_path.relative_to(ROOT)}", flush=True)
    for t, r in results.items():
        print(f"  {t:<8}: {r['final_score']:.1f}/100  (llm {r['llm_norm']:.3f}, "
              f"struct {r['structural_passed']}/{r['structural_total']})", flush=True)
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
