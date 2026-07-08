#!/usr/bin/env python3
"""
Phase 0 spike — prove AutoRubric works against a real EDB brief via OpenRouter.

This is a throwaway proof-of-concept, NOT the production evaluator. It exists to
confirm three things before we commit to the full port:
  1. AutoRubric + LiteLLM can reach our OpenRouter key.
  2. Per-criterion (atomic) grading returns sane verdicts on a real brief.
  3. We can see the score + token cost so we can budget the full N×M×J version.

The existing regex+holistic evaluator in ../eval/ is left completely untouched so
the two frameworks can be compared side by side later.

Usage:
  venv/bin/python -m eval_autorubric.spike [brief_path]
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

from autorubric import Criterion, LLMConfig, Rubric
from autorubric.graders import CriterionGrader

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Cheap judge for the spike; the real evaluator can use a stronger / ensemble panel.
# LiteLLM routes the `openrouter/` prefix to OpenRouter using OPENROUTER_API_KEY.
JUDGE_MODEL = "openrouter/anthropic/claude-haiku-4-5"

DEFAULT_BRIEF = ROOT / "outputs" / "brief_v2_2026-07-06_1209.md"

# The mandate context the judge grades against (the brief's implicit "query").
QUERY = (
    "This is the Emirates Development Bank (EDB) daily macro intelligence brief. "
    "EDB is a government-owned development finance institution pursuing Operation "
    "300bn (grow industrial GDP to AED 300bn by 2031) across five priority sectors: "
    "advanced technology, manufacturing, healthcare, renewables, food security. "
    "The AED is pegged to USD at 3.6725, so US rate moves transmit via CBUAE -> "
    "EIBOR -> EDB's floating-rate SME portfolio."
)

# A deliberately small 3-criterion toy rubric spanning the patterns we care about:
#   - a BINARY structural criterion (cheap, high-reliability)
#   - an ORDINAL quality criterion (1-5 with behavioural anchors)
#   - a NEGATIVE penalty criterion (something our current rubric cannot express)
TOY_RUBRIC = Rubric([
    Criterion(
        name="peg_chain_traced",
        weight=10.0,
        requirement=(
            "The brief explicitly traces the AED/USD peg transmission chain from a "
            "Fed rate move through CBUAE, then EIBOR, then EDB's floating-rate loan "
            "portfolio / SME debt serviceability. All four links must appear."
        ),
    ),
    Criterion(
        name="mandate_relevance",
        weight=10.0,
        requirement=(
            "Every macro signal is mapped to at least one of EDB's five priority "
            "sectors with a specific, quantified sector impact. Score 5 if all signals "
            "are sector-mapped with quantified impact and there is zero generic market "
            "commentary; 3 if roughly half are mapped with some generic filler; 1 if "
            "there is no EDB mandate framing at all."
        ),
    ),
    Criterion(
        name="generic_market_commentary",
        weight=-8.0,  # NEGATIVE weight = penalty for an anti-pattern
        requirement=(
            "The brief contains generic market commentary not tied to EDB's mandate "
            "or the five priority sectors (e.g. broad equity-market color, retail "
            "investor advice). This is an anti-pattern; MET means the flaw is present."
        ),
    ),
])


async def main() -> None:
    brief_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BRIEF
    if not brief_path.exists():
        sys.exit(f"Brief not found: {brief_path}")

    brief_text = brief_path.read_text(encoding="utf-8")
    print(f"Judge model : {JUDGE_MODEL}")
    print(f"Brief       : {brief_path.name} ({len(brief_text):,} chars)")
    print(f"Criteria    : {len(TOY_RUBRIC.rubric)} "
          f"(1 binary structural, 1 ordinal quality, 1 negative penalty)\n")

    grader = CriterionGrader(
        llm_config=LLMConfig(
            model=JUDGE_MODEL,
            temperature=0.0,
            max_parallel_requests=5,
        )
    )

    result = await TOY_RUBRIC.grade(
        to_grade=brief_text,
        grader=grader,
        query=QUERY,
    )

    print("── Per-criterion verdicts ──────────────────────────────────────────")
    for cr in result.report:
        name = cr.criterion.name or cr.criterion.requirement[:40]
        print(f"[{cr.final_verdict:<13}] {name}  (w={cr.criterion.weight:+.0f})")
        reason = (cr.final_reason or "").strip().replace("\n", " ")
        print(f"    -> {reason[:220]}")
    print("────────────────────────────────────────────────────────────────────")
    score = result.score
    print(f"\nNormalized score : {score:.3f}" if score is not None else "\nScore: n/a")

    cost = getattr(result, "completion_cost", None)
    print(f"Completion cost  : ${cost:.5f}" if cost else "Completion cost  : n/a (unreported by OpenRouter)")

    usage = getattr(result, "token_usage", None)
    if usage:
        print(f"Token usage      : {usage}")
    print(f"CANNOT_ASSESS    : {result.cannot_assess_count}")


if __name__ == "__main__":
    asyncio.run(main())
