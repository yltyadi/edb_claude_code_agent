"""
AutoRubric rubric definition for EDB macro briefs.

Follows the paper's API exactly (Listings 1–3 in Rao & Callison-Burch):

  rubric = Rubric([
      Criterion(weight=0.10, requirement="...",               # binary (structural)
      Criterion(weight=0.20, requirement="...", scale_type="ordinal", options=[...]),
      Criterion(weight=-0.10, requirement="..."),             # negative (penalty)
  ])

Three criterion types:
  BINARY   — structural / format requirements (positive weight, MET = present = good)
  ORDINAL  — quality dimensions (positive weight, 5-level descriptive labels)
  PENALTY  — anti-patterns (negative weight, MET = anti-pattern present = bad)

Weight calibration:
  Binary sum  ≈ 0.76  (~40% of positive total)
  Ordinal sum = 1.00  (~60% of positive total)
  This preserves the spirit of the old 40/60 structural/LLM split, but without
  any regex — an LLM judge assesses semantic compliance, removing the reward-hacking
  vector that pattern-matched structural checks create.
"""

from __future__ import annotations

import sys
from pathlib import Path

from autorubric import Rubric, Criterion

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.rubric import LLM_DIMENSIONS  # noqa: E402  (the 7 shared ordinal dimensions)

# ── ordinal options (5-level descriptive labels) ─────────────────────────────
# Descriptive labels avoid collision with the judge's shuffled option positions:
# if the model writes "1" it means "first option listed", not "semantic level 1".
_OPTS_5 = [
    {"label": "Absent",    "value": 0.00},
    {"label": "Weak",      "value": 0.25},
    {"label": "Adequate",  "value": 0.50},
    {"label": "Strong",    "value": 0.75},
    {"label": "Exemplary", "value": 1.00},
]


# ── binary structural criteria ────────────────────────────────────────────────
# Each criterion states a structural or format requirement in plain language.
# MET = requirement is satisfied (positive contribution to result.score).
# Collectively these replace the 20 legacy regex checks without exposing patterns
# the agent can game by literal string insertion.
BINARY_CRITERIA = [
    {
        "id": "sections_complete",
        "weight": 0.10,
        "requirement": (
            "The brief contains all three required audience sections: a Type A Executive "
            "Brief (headline plus a five-sector impact matrix), a Type B Credit Team Alert "
            "(at least one calculation and a clear action flag), and a Type C Stakeholder "
            "Bulletin (What happened / What it means / What to consider, each substantive)."
        ),
    },
    {
        "id": "sector_matrix_complete",
        "weight": 0.10,
        "requirement": (
            "The sector impact matrix explicitly addresses all five EDB priority sectors "
            "(Advanced Technology, Manufacturing, Healthcare, Renewables, Food Security), "
            "with a named direction and at least one data-justified impact per row — not a "
            "placeholder or a row that says 'no direct signal'."
        ),
    },
    {
        "id": "required_calculations_present",
        "weight": 0.10,
        "requirement": (
            "At least two of the four required quantitative calculations are present with "
            "visible arithmetic steps: (1) EIBOR interest-rate sensitivity for the reference "
            "AED 5M loan with ±25bps scenarios shown in AED annual debt service; (2) oil "
            "price or fiscal impact translated to an AED figure; (3) petrochemical feedstock "
            "cost pass-through; (4) Operation 300bn annual run-rate against the AED 300bn target."
        ),
    },
    {
        "id": "sources_with_vintage_dates",
        "weight": 0.08,
        "requirement": (
            "A Sources section is present that names every data series used in the brief "
            "and includes the date (vintage) of each value. Any series with a value date "
            "more than 7 days before the brief date is explicitly flagged as stale."
        ),
    },
    {
        "id": "peg_chain_traced",
        "weight": 0.08,
        "requirement": (
            "The AED/USD peg transmission chain is explicitly traced in the brief body: "
            "starting from the Federal Reserve decision, through the CBUAE Base Rate "
            "adjustment, to the EIBOR 3M shift, and finally to the impact on EDB's "
            "floating-rate SME loan portfolio."
        ),
    },
    {
        "id": "watch_list_specific",
        "weight": 0.07,
        "requirement": (
            "A forward-looking watch list for the next 72 hours is present with at least "
            "three named, specific upcoming events, data releases, or decision dates. "
            "Generic phrases such as 'monitor oil prices' do not count — each item must "
            "name a concrete event or scheduled release."
        ),
    },
    {
        "id": "action_flag_with_rationale",
        "weight": 0.07,
        "requirement": (
            "At least one explicit action flag (MONITOR, REVIEW, or ESCALATE) is present "
            "with a specific, evidence-based rationale tied to a named EDB portfolio "
            "exposure, sector, or mandate threshold."
        ),
    },
    {
        "id": "calculation_block_aed",
        "weight": 0.06,
        "requirement": (
            "At least one code block (delimited by triple backticks) is present and "
            "contains AED-denominated figures with visible arithmetic — not just a stated "
            "conclusion. The calculation must show intermediate steps."
        ),
    },
    {
        "id": "header_metadata_complete",
        "weight": 0.05,
        "requirement": (
            "The brief header contains all required metadata: a Date field, an Agent "
            "version indicator (e.g. v2), and a count of signals processed or passing "
            "the mandate filter."
        ),
    },
    {
        "id": "prior_state_referenced",
        "weight": 0.05,
        "requirement": (
            "The brief references at least one piece of temporal context from a prior run: "
            "a streak count, the number of consecutive days a rate has been unchanged, or "
            "an explicit comparison to a prior-session baseline — demonstrating continuity "
            "across sessions rather than treating each brief as stateless."
        ),
    },
]

# ── negative penalty criteria ─────────────────────────────────────────────────
# MET = anti-pattern IS present (bad). Negative weight penalises the final score.
# Weights are on the same scale as ordinal/binary weights to avoid score collapse.
PENALTIES = [
    {
        "id": "generic_market_commentary",
        "weight": -0.06,
        "requirement": (
            "The brief contains generic market commentary NOT tied to EDB's five "
            "priority sectors (advanced technology, manufacturing, healthcare, renewables, "
            "food security) or the AED/USD peg chain. Broad equity-index color, or macro "
            "narration with no EDB/sector implication, counts as the anti-pattern."
        ),
    },
    {
        "id": "silent_stale_or_estimated_data",
        "weight": -0.10,
        "requirement": (
            "The brief uses a stale data value or an estimated rate (especially EIBOR) "
            "in a calculation WITHOUT explicitly disclosing that it is stale or estimated "
            "at the point of use. A clearly disclosed estimate is acceptable; a silent one "
            "is the anti-pattern."
        ),
    },
    {
        "id": "unsupported_number",
        "weight": -0.15,
        "requirement": (
            "The brief states a material quantitative figure — a rate, price, AED amount, "
            "or percentage driving a conclusion — that cannot be traced to any named source "
            "or calculation shown in the brief (a likely hallucinated number)."
        ),
    },
]

BINARY_IDS  = [c["id"] for c in BINARY_CRITERIA]
ORDINAL_IDS = [d["id"] for d in LLM_DIMENSIONS]
PENALTY_IDS = [p["id"] for p in PENALTIES]


def _binary(c: dict) -> Criterion:
    return Criterion(name=c["id"], weight=c["weight"], requirement=c["requirement"])


def _ordinal(dim: dict) -> Criterion:
    anchors = " | ".join(
        f"{lvl}/5: {dim['scale'][lvl]}" for lvl in sorted(dim["scale"])
    )
    return Criterion(
        name=dim["id"],
        weight=float(dim["weight"]),
        requirement=f"{dim['description']} Behavioural anchors — {anchors}",
        scale_type="ordinal",
        options=_OPTS_5,
    )


def build_rubric() -> Rubric:
    """10 binary structural + 7 ordinal quality + 3 negative penalty criteria."""
    criteria  = [_binary(c) for c in BINARY_CRITERIA]
    criteria += [_ordinal(d) for d in LLM_DIMENSIONS]
    criteria += [_binary(p) for p in PENALTIES]   # penalties are also binary
    return Rubric(criteria)
