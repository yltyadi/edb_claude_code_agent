#!/usr/bin/env python3
"""
Head-to-head: OLD evaluator (one conflated LLM call) vs NEW AutoRubric (atomic per-criterion).

Both paths use:
  - the SAME judge model (via OpenRouter)
  - the SAME 7 dimension definitions + scales (imported from eval/rubric.py)
  - the SAME regex auto-check layer (40%) and 40/60 aggregation

The ONLY difference is HOW the 7 LLM dimensions are judged:
  OLD  → one LLM call scores all 7 dims at once (holistic / conflated)
  NEW  → AutoRubric scores each dimension in its own LLM call (atomic per-criterion)

This isolates the paper's central claim so the two approaches can be compared directly.

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

from autorubric import Criterion, LLMConfig, Rubric
from autorubric.graders import CriterionGrader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from eval.rubric import AUTOMATED_CHECKS, LLM_DIMENSIONS, AUTO_WEIGHT, LLM_WEIGHT  # noqa: E402

JUDGE_MODEL = "openrouter/anthropic/claude-haiku-4-5"
DEFAULT_BRIEF = ROOT / "outputs" / "brief_v2_2026-07-06_1209.md"

QUERY = (
    "This is the Emirates Development Bank (EDB) daily macro intelligence brief. "
    "EDB is a government-owned development finance institution pursuing Operation "
    "300bn (grow industrial GDP to AED 300bn by 2031) across five priority sectors: "
    "advanced technology, manufacturing, healthcare, renewables, food security. "
    "The AED is pegged to USD at 3.6725, so US rate moves transmit via CBUAE → "
    "EIBOR → EDB's floating-rate SME portfolio."
)

# 5-level ordinal options — plain dicts as shown in the paper (Listing 2)
_OPTS_5 = [
    {"label": "Absent",    "value": 0.00},
    {"label": "Weak",      "value": 0.25},
    {"label": "Adequate",  "value": 0.50},
    {"label": "Strong",    "value": 0.75},
    {"label": "Exemplary", "value": 1.00},
]


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


# ── NEW path: AutoRubric atomic per-criterion scoring (Listing 2 + 4 pattern) ─
def build_autorubric() -> Rubric:
    """Build a 7-criterion rubric using plain dict options — paper Listing 2."""
    criteria = []
    for d in LLM_DIMENSIONS:
        anchors = " | ".join(
            f"{lvl}/5: {d['scale'][lvl]}" for lvl in sorted(d["scale"])
        )
        criteria.append(Criterion(
            name=d["id"],
            weight=float(d["weight"]),
            requirement=f"{d['description']} Anchors — {anchors}",
            scale_type="ordinal",
            options=_OPTS_5,
        ))
    return Rubric(criteria)


async def new_llm_scores(brief: str) -> dict[str, int]:
    """Grade with AutoRubric (Listing 4: single judge) and convert to 1-5 levels."""
    grader = CriterionGrader(
        llm_config=LLMConfig(model=JUDGE_MODEL, temperature=0.0,
                             max_parallel_requests=5),
    )
    result = await build_autorubric().grade(to_grade=brief, grader=grader, query=QUERY)
    scores = {}
    for cr in result.report:
        val = cr.score_value   # 0.0–1.0 from AutoRubric
        scores[cr.criterion.name] = round(val * 4) + 1 if val is not None else 0
    return scores


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
