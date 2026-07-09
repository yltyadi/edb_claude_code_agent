"""
AutoRubric evaluator — core grading engine.

Follows the paper's Listing 4 API:

  result = await rubric.grade(to_grade=text, grader=grader, query=QUERY)
  final_score = result.score * 100   # AutoRubric handles all weighting internally

No separate structural layer — binary, ordinal, and penalty criteria are all in one
Rubric so result.score is the single authoritative weighted output.
"""

from __future__ import annotations

import asyncio
import re

from autorubric import LLMConfig
from autorubric.graders import CriterionGrader, JudgeSpec

from eval_autorubric.config import QUERY, judge_models
from eval_autorubric.rubric_def import (
    BINARY_IDS, ORDINAL_IDS, PENALTY_IDS, build_rubric,
)


def _make_grader(models: list[str]) -> CriterionGrader:
    """Single judge or majority-vote ensemble — paper Listing 4."""
    def cfg(m):
        return LLMConfig(model=m, temperature=0.0, max_parallel_requests=6)

    if len(models) == 1:
        return CriterionGrader(llm_config=cfg(models[0]))

    judges = [
        JudgeSpec(cfg(m), m.split("/")[-1], weight=1.0)
        for m in models
    ]
    return CriterionGrader(judges=judges, aggregation="majority")


def _score_to_level(val) -> int | None:
    """Convert 0.0–1.0 ordinal value to 1–5 display level."""
    return round(val * 4) + 1 if val is not None else None


def _is_met(val) -> bool:
    """Binary criterion is MET when score_value ≈ 1.0."""
    return val is not None and val >= 0.9


async def grade_brief(text: str, brief_type: str, models: list[str] | None = None) -> dict:
    models = models or judge_models()
    rubric  = build_rubric()
    grader  = _make_grader(models)

    # Paper Listing 4 — result.score is the normalized weighted score (0.0–1.0)
    result = await rubric.grade(to_grade=text, grader=grader, query=QUERY)

    llm_score = result.score
    mean_agr  = getattr(result, "mean_agreement", None)

    binary, dims, penalties, reasons, agreement = {}, {}, {}, {}, {}

    for cr in result.report:
        cid    = cr.criterion.name
        val    = cr.score_value
        reason = re.sub(r"^[\w.-]+:\s*", "", (cr.final_reason or "").strip())
        reasons[cid] = reason

        agr = getattr(cr, "agreement", None)
        if agr is not None:
            agreement[cid] = agr

        if cid in BINARY_IDS:
            binary[cid] = _is_met(val)
        elif cid in ORDINAL_IDS:
            dims[cid] = _score_to_level(val)
        elif cid in PENALTY_IDS:
            penalties[cid] = _is_met(val)

    return {
        "brief_type":    brief_type,
        "binary":        binary,
        "dims":          dims,
        "penalties":     penalties,
        "reasons":       reasons,
        "agreement":     agreement,
        "mean_agreement": mean_agr,
        "llm_score":     llm_score,
        "final_score":   llm_score * 100,
        "judges":        models,
        "ensemble":      len(models) >= 2,
        "total_tokens":  getattr(
            getattr(result, "token_usage", None), "total_tokens", None
        ),
    }


async def grade_all(briefs: dict[str, str], models: list[str] | None = None) -> dict:
    """Grade all available briefs concurrently and compute cross-version deltas."""
    models = models or judge_models()
    types  = [t for t, txt in briefs.items() if txt]
    graded = await asyncio.gather(
        *(grade_brief(briefs[t], t, models) for t in types)
    )
    results = {t: g for t, g in zip(types, graded)}

    def score(t):
        return results[t]["final_score"] if t in results else None

    deltas = {}
    if score("v2") is not None and score("v1") is not None:
        deltas["v2_vs_v1"]  = score("v2") - score("v1")
    if score("v2") is not None and score("general") is not None:
        deltas["v2_vs_gen"] = score("v2") - score("general")
    if score("v1") is not None and score("general") is not None:
        deltas["v1_vs_gen"] = score("v1") - score("general")

    return {"results": results, "deltas": deltas, "judges": models,
            "ensemble": len(models) >= 2}
