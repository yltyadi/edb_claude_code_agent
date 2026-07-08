"""
AutoRubric evaluator — core grading engine.

grade_brief()  -> grade one brief, return a structured result dict.
grade_all()    -> grade a {type: text} map (v2/v1/general) + compute deltas.

Both are async. Each brief's criteria are graded atomically (one LLM call per
criterion per judge) with concurrency; briefs are graded concurrently too.
"""

from __future__ import annotations

import asyncio
import re

from autorubric import LLMConfig
from autorubric.graders import CriterionGrader, JudgeSpec

from eval_autorubric.config import (
    AUTO_WEIGHT, LLM_WEIGHT, QUERY, TREND_CAP_FOR_STATELESS, TREND_DIMENSION_ID,
    judge_models,
)
from eval_autorubric.rubric_def import (
    ORDINAL_IDS, PENALTY_IDS, PENALTIES, LABEL_TO_LEVEL, build_rubric, _WEIGHT_SCALE,
)
from eval_autorubric.structural import run_structural, structural_pct

from eval.rubric import LLM_DIMENSIONS

_DIM_WEIGHT = {d["id"]: d["weight"] * _WEIGHT_SCALE for d in LLM_DIMENSIONS}
_PEN_WEIGHT = {p["id"]: p["weight"] for p in PENALTIES}
_STATELESS_TYPES = {"v1", "general"}


def _make_grader(models: list[str]) -> CriterionGrader:
    """Single judge if one model; diverse-model ensemble (majority vote) if >=2."""
    def cfg(model: str) -> LLMConfig:
        return LLMConfig(
            model=model, temperature=0.0, max_parallel_requests=6,
            cache_enabled=True, prompt_caching=True,
        )
    if len(models) == 1:
        return CriterionGrader(llm_config=cfg(models[0]))
    judges = [JudgeSpec(cfg(m), judge_id=m.split("/")[-1]) for m in models]
    return CriterionGrader(judges=judges, aggregation="majority")


def _ordinal_level(cr) -> int | None:
    """1-5 level, or None if the judge abstained (CANNOT_ASSESS / NA)."""
    mc = cr.final_multi_choice_verdict
    if mc is not None:
        if getattr(mc, "na", False):
            return None
        level = LABEL_TO_LEVEL.get(mc.selected_label)
        if level is not None:
            return level
    val = cr.score_value
    return round(val * 4) + 1 if val is not None else None


def _penalty_met(cr) -> bool:
    """True only if the anti-pattern is confirmed present (verdict MET)."""
    v = cr.final_verdict
    if v is None:
        return False
    name = getattr(v, "name", str(v).rsplit(".", 1)[-1]).upper()
    return name == "MET"


def _normalized_llm_score(dims: dict[str, int | None], penalties: dict[str, bool]) -> float:
    """AutoRubric scoring formula, recomputed so the trend cap is reflected.

    score = max(0, min(1, sum(v_i * w_i) / sum(w_i for w_i > 0)))
    ordinal v = (level-1)/4 ; penalty v = 1 if MET else 0 (negative weight).
    Abstained (None) dimensions are excluded from BOTH numerator and denominator
    (AutoRubric's default SKIP strategy for CANNOT_ASSESS).
    """
    scored = {i: lvl for i, lvl in dims.items() if lvl is not None}
    num = sum(((lvl - 1) / 4.0) * _DIM_WEIGHT[i] for i, lvl in scored.items())
    num += sum((1.0 if penalties.get(i) else 0.0) * _PEN_WEIGHT[i] for i in PENALTY_IDS)
    denom = sum(_DIM_WEIGHT[i] for i in scored if _DIM_WEIGHT[i] > 0)
    return max(0.0, min(1.0, num / denom)) if denom else 0.0


async def grade_brief(text: str, brief_type: str, models: list[str] | None = None) -> dict:
    models = models or judge_models()
    grader = _make_grader(models)
    result = await build_rubric().grade(to_grade=text, grader=grader, query=QUERY)

    dims, penalties, reasons, agreement = {}, {}, {}, {}
    for cr in result.report:
        cid = cr.criterion.name
        reason = (cr.final_reason or "").strip()
        # final_reason is prefixed with the judge id ("default: ...", "gpt: ...")
        reason = re.sub(r"^[\w.-]+:\s*", "", reason)
        reasons[cid] = reason
        if cr.agreement is not None:
            agreement[cid] = cr.agreement
        if cid in ORDINAL_IDS:
            dims[cid] = _ordinal_level(cr)
        elif cid in PENALTY_IDS:
            penalties[cid] = _penalty_met(cr)

    # domain rule: stateless briefs cannot score trend depth above the cap
    if brief_type in _STATELESS_TYPES and TREND_DIMENSION_ID in dims:
        dims[TREND_DIMENSION_ID] = min(dims[TREND_DIMENSION_ID], TREND_CAP_FOR_STATELESS)

    structural = run_structural(text)
    s_pct = structural_pct(structural)
    llm_norm = _normalized_llm_score(dims, penalties)
    final = (s_pct * AUTO_WEIGHT + llm_norm * LLM_WEIGHT) * 100

    usage = result.token_usage
    mean_agr = sum(agreement.values()) / len(agreement) if agreement else None

    return {
        "brief_type": brief_type,
        "structural": structural,
        "structural_passed": sum(1 for v in structural.values() if v),
        "structural_total": len(structural),
        "dims": dims,
        "penalties": penalties,
        "reasons": reasons,
        "agreement": agreement,
        "mean_agreement": mean_agr,
        "llm_norm": llm_norm,
        "final_score": final,
        "judges": models,
        "ensemble": len(models) >= 2,
        "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
    }


async def grade_all(briefs: dict[str, str], models: list[str] | None = None) -> dict:
    """briefs = {"v2": text, "v1": text|None, "general": text|None}."""
    models = models or judge_models()
    types = [t for t, txt in briefs.items() if txt]
    graded = await asyncio.gather(
        *(grade_brief(briefs[t], t, models) for t in types)
    )
    results = {t: g for t, g in zip(types, graded)}

    def score(t: str) -> float | None:
        return results[t]["final_score"] if t in results else None

    deltas = {}
    if score("v2") is not None and score("v1") is not None:
        deltas["v2_vs_v1"] = score("v2") - score("v1")
    if score("v2") is not None and score("general") is not None:
        deltas["v2_vs_gen"] = score("v2") - score("general")
    if score("v1") is not None and score("general") is not None:
        deltas["v1_vs_gen"] = score("v1") - score("general")

    return {"results": results, "deltas": deltas, "judges": models,
            "ensemble": len(models) >= 2}
