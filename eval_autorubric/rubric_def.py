"""
AutoRubric rubric definition for the EDB macro brief.

Structure (mirrors the paper's analytic-rubric design):
  - 7 ORDINAL quality dimensions (1-5, behavioural anchors) — imported verbatim
    from the OLD rubric (eval/rubric.py) so the two frameworks judge the SAME
    constructs and the comparison is fair.
  - 3 NEGATIVE penalty criteria — anti-patterns the old rubric could not express.
    Negative weights counteract the documented leniency bias of LLM judges.

The 20 regex structural checks are NOT LLM-judged here; they stay deterministic
(see structural.py) and form the same 40% structural layer as the old framework.
"""

from __future__ import annotations

import sys
from pathlib import Path

from autorubric import Criterion, CriterionOption, Rubric

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.rubric import LLM_DIMENSIONS  # noqa: E402  (the 7 shared dimensions)

# Weights are scaled to integers purely for readable YAML/printouts; AutoRubric
# normalises them internally, so relative magnitude is all that matters.
_WEIGHT_SCALE = 100.0

# Ordinal options use DESCRIPTIVE labels, not "1".."5". Numeric labels collide
# with the judge's shuffled presentation positions (it says "1" meaning the
# first-listed option, which AutoRubric then misreads as the semantic level 1).
# Descriptive labels remove that collision and give the judge clean anchors.
LEVEL_LABELS = {5: "exemplary", 4: "strong", 3: "adequate", 2: "weak", 1: "absent"}
LABEL_TO_LEVEL = {v: k for k, v in LEVEL_LABELS.items()}

# ── negative penalty criteria (new capability vs the old rubric) ────────────
PENALTIES = [
    {
        "id": "generic_market_commentary",
        "weight": -8.0,
        "requirement": (
            "The brief contains generic market commentary NOT tied to EDB's mandate "
            "or its five priority sectors — e.g. broad equity-index color, retail "
            "trading views, or macro narration with no EDB/sector implication. "
            "MET means this anti-pattern is present (bad)."
        ),
    },
    {
        "id": "silent_stale_or_estimated_data",
        "weight": -10.0,
        "requirement": (
            "The brief uses a stale data value or an estimated rate (especially "
            "EIBOR) in a calculation WITHOUT disclosing that it is stale/estimated "
            "at the point of use. A disclosed estimate is fine; a silent one is the "
            "anti-pattern. MET means an undisclosed stale/estimated input is present."
        ),
    },
    {
        "id": "unsupported_number",
        "weight": -12.0,
        "requirement": (
            "The brief states a material quantitative figure (a rate, price, AED "
            "amount, or percentage driving a conclusion) that has no traceable "
            "source anywhere in the brief — i.e. a likely hallucination. MET means "
            "at least one such unsupported material number is present."
        ),
    },
]


def _ordinal_criterion(dim: dict) -> Criterion:
    """Turn a rubric.py dimension (1-5 scale + anchors) into an ordinal Criterion."""
    options = [
        CriterionOption(label=LEVEL_LABELS[lvl], value=(lvl - 1) / 4.0,
                        description=f"(level {lvl}/5) {dim['scale'][lvl]}")
        for lvl in sorted(dim["scale"])
    ]
    return Criterion(
        name=dim["id"],
        weight=dim["weight"] * _WEIGHT_SCALE,
        requirement=dim["description"],
        options=options,
        scale_type="ordinal",
    )


def _penalty_criterion(p: dict) -> Criterion:
    """A binary MET/UNMET anti-pattern with a negative weight."""
    return Criterion(name=p["id"], weight=p["weight"], requirement=p["requirement"])


def build_rubric() -> Rubric:
    criteria = [_ordinal_criterion(d) for d in LLM_DIMENSIONS]
    criteria += [_penalty_criterion(p) for p in PENALTIES]
    return Rubric(criteria)


# convenience: which criterion ids are ordinal dims vs penalties
ORDINAL_IDS = [d["id"] for d in LLM_DIMENSIONS]
PENALTY_IDS = [p["id"] for p in PENALTIES]
