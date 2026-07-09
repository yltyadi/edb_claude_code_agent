"""
AutoRubric evaluator — configuration.

Judges are driven by env vars so the same engine runs unchanged from the Claude
Code skill and from the deployed HF Space:

  AUTORUBRIC_JUDGES   comma-separated LiteLLM model ids (≥2 enables ensemble +
                      inter-judge reliability). Default: 2-model cross-family
                      ensemble (Claude Haiku + Gemini Flash), matching the paper's
                      Listing 4 recommendation for diverse-family judging.
  OPENROUTER_API_KEY  read automatically by LiteLLM for the openrouter/ prefix.

Example override:
  export AUTORUBRIC_JUDGES="openrouter/anthropic/claude-haiku-4-5,openrouter/openai/gpt-4.1-mini"
"""

from __future__ import annotations

import os

# 2-model cross-family default (paper Listing 4: diverse model families for ensemble)
_DEFAULT_JUDGES = [
    "openrouter/anthropic/claude-haiku-4-5",   # Anthropic family
    "openrouter/google/gemini-2.5-flash",       # Google family
]


def judge_models() -> list[str]:
    raw = os.environ.get("AUTORUBRIC_JUDGES", "").strip()
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    return list(_DEFAULT_JUDGES)


# Same 40/60 aggregation as the legacy framework — only the LLM judging method differs.
AUTO_WEIGHT = 0.40   # deterministic regex structural checks
LLM_WEIGHT  = 0.60   # AutoRubric result.score (normalized, atomic per-criterion)

# Mandate context sent as the `query` argument in rubric.grade() — every judge
# grades against this framing (paper Listing 4: query=prompt).
QUERY = (
    "This is the Emirates Development Bank (EDB) daily macro intelligence brief. "
    "EDB is a government-owned development finance institution pursuing Operation "
    "300bn (grow industrial GDP to AED 300bn by 2031) across five priority sectors: "
    "advanced technology, manufacturing, healthcare, renewables, food security. "
    "The AED is pegged to USD at 3.6725, so US rate moves transmit via CBUAE → "
    "EIBOR → EDB's floating-rate SME portfolio. Grade the brief as a specialist "
    "macro-credit analyst would: reward specific, sourced, sector-mapped, "
    "quantified analysis and penalise generic commentary or undisclosed estimates."
)
