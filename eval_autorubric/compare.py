#!/usr/bin/env python3
"""
Small head-to-head: OLD evaluator vs NEW AutoRubric evaluator on ONE brief.

Both paths use:
  - the SAME judge model (via OpenRouter)
  - the SAME 7 dimension definitions + scales (imported from eval/rubric.py)
  - the SAME regex auto-check layer (40%) and the SAME 40/60 aggregation

The ONLY thing that differs is HOW the 7 LLM dimensions are judged:
  OLD  -> one LLM call scores all 7 dimensions at once   (holistic / conflated)
  NEW  -> AutoRubric scores each dimension in its own call (atomic per-criterion)

This isolates the paper's central claim (atomic decomposition beats conflated
holistic scoring) so it can be shown side by side. The production eval_autorubric
rubric will be richer; this is a controlled comparison, not the final design.

Usage:
  venv/bin/python -m eval_autorubric.compare [brief_path]
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
import litellm

from autorubric import Criterion, CriterionOption, LLMConfig, Rubric
from autorubric.graders import CriterionGrader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from eval.rubric import (  # noqa: E402
    AUTOMATED_CHECKS, LLM_DIMENSIONS, AUTO_WEIGHT, LLM_WEIGHT,
)
from eval_autorubric.rubric_def import LEVEL_LABELS, LABEL_TO_LEVEL  # noqa: E402

JUDGE_MODEL = "openrouter/anthropic/claude-haiku-4-5"
DEFAULT_BRIEF = ROOT / "outputs" / "brief_v2_2026-07-06_1209.md"

QUERY = (
    "This is the Emirates Development Bank (EDB) daily macro intelligence brief. "
    "EDB is a government-owned development finance institution pursuing Operation "
    "300bn (grow industrial GDP to AED 300bn by 2031) across five priority sectors: "
    "advanced technology, manufacturing, healthcare, renewables, food security. "
    "The AED is pegged to USD at 3.6725, so US rate moves transmit via CBUAE -> "
    "EIBOR -> EDB's floating-rate SME portfolio."
)


# ── shared: regex auto layer (identical for both) ──────────────────────────
def run_auto_checks(text: str) -> tuple[int, int]:
    passed = sum(
        1 for c in AUTOMATED_CHECKS
        if re.search(c["pattern"], text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    )
    return passed, len(AUTOMATED_CHECKS)


def dims_block() -> str:
    lines = []
    for d in LLM_DIMENSIONS:
        scale = " | ".join(f"{k}={v}" for k, v in sorted(d["scale"].items()))
        lines.append(f"- {d['id']} ({d['name']}, weight {d['weight']}): "
                     f"{d['description']}\n    SCALE: {scale}")
    return "\n".join(lines)


# ── OLD path: one conflated LLM call scoring all 7 dims ─────────────────────
def old_llm_scores(brief: str) -> dict[str, int]:
    prompt = f"""You are scoring ONE Emirates Development Bank macro brief on 7 dimensions.
Score each dimension 1-5 (integers) using the scales below.

{QUERY}

DIMENSIONS:
{dims_block()}

--- BRIEF ---
{brief}

Respond with ONLY valid JSON mapping each dimension id to its 1-5 score:
{{{", ".join(f'"{d["id"]}": N' for d in LLM_DIMENSIONS)}}}"""
    resp = litellm.completion(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    raw = resp.choices[0].message.content
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    data = json.loads(m.group(0))
    return {d["id"]: int(data.get(d["id"], 0)) for d in LLM_DIMENSIONS}


# ── NEW path: AutoRubric atomic per-criterion scoring of the same 7 dims ────
def build_autorubric() -> Rubric:
    criteria = []
    for d in LLM_DIMENSIONS:
        options = [
            CriterionOption(label=LEVEL_LABELS[lvl], value=(lvl - 1) / 4.0,
                            description=f"(level {lvl}/5) {d['scale'][lvl]}")
            for lvl in sorted(d["scale"])
        ]
        criteria.append(Criterion(
            name=d["id"], weight=d["weight"], requirement=d["description"],
            options=options, scale_type="ordinal",
        ))
    return Rubric(criteria)


def report_to_1_5(cr) -> int:
    """Recover the 1-5 level AutoRubric chose for an ordinal criterion."""
    mc = cr.final_multi_choice_verdict
    if mc is not None and not getattr(mc, "na", False):
        level = LABEL_TO_LEVEL.get(mc.selected_label)
        if level is not None:
            return level
    val = cr.score_value                        # property, 0.0 - 1.0
    if val is not None:
        return round(val * 4) + 1
    return 0


async def new_llm_scores(brief: str) -> dict[str, int]:
    grader = CriterionGrader(
        llm_config=LLMConfig(model=JUDGE_MODEL, temperature=0.0,
                             max_parallel_requests=5),
    )
    result = await build_autorubric().grade(to_grade=brief, grader=grader, query=QUERY)
    return {cr.criterion.name: report_to_1_5(cr) for cr in result.report}


# ── aggregation (identical formula for both) ────────────────────────────────
def llm_pct(scores: dict[str, int]) -> float:
    total = sum(scores.get(d["id"], 0) * d["weight"] for d in LLM_DIMENSIONS)
    return total / 5.0


def final_score(auto_passed: int, auto_total: int, scores: dict[str, int]) -> float:
    auto = auto_passed / auto_total
    return (auto * AUTO_WEIGHT + llm_pct(scores) * LLM_WEIGHT) * 100


async def main() -> None:
    brief_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BRIEF
    brief = brief_path.read_text(encoding="utf-8")

    auto_passed, auto_total = run_auto_checks(brief)

    print(f"Brief : {brief_path.name}")
    print(f"Judge : {JUDGE_MODEL}")
    print(f"Auto  : {auto_passed}/{auto_total} regex checks (identical for both)\n")
    print("Scoring OLD (1 conflated call) and NEW (7 atomic calls)...\n")

    old, new = old_llm_scores(brief), await new_llm_scores(brief)

    print(f"{'Dimension':<26}{'wt':>5}{'OLD':>6}{'NEW':>6}{'Δ':>5}")
    print("─" * 48)
    for d in LLM_DIMENSIONS:
        o, n = old.get(d["id"], 0), new.get(d["id"], 0)
        flag = "" if o == n else "  <-- differs"
        print(f"{d['id']:<26}{d['weight']*100:>4.0f}%{o:>6}{n:>6}{n-o:>+5}{flag}")

    old_f = final_score(auto_passed, auto_total, old)
    new_f = final_score(auto_passed, auto_total, new)
    print("─" * 48)
    print(f"{'LLM subscore (of 60)':<26}{'':>5}{llm_pct(old)*100*LLM_WEIGHT:>6.1f}"
          f"{llm_pct(new)*100*LLM_WEIGHT:>6.1f}")
    print(f"{'FINAL / 100':<26}{'':>5}{old_f:>6.1f}{new_f:>6.1f}{new_f-old_f:>+5.1f}")
    print(f"\nDimensions where the two judges disagree: "
          f"{sum(1 for d in LLM_DIMENSIONS if old.get(d['id']) != new.get(d['id']))}/7")


if __name__ == "__main__":
    asyncio.run(main())
