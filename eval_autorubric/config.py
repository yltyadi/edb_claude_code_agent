"""
AutoRubric evaluator — configuration.

Judges are driven by env vars so the same engine runs unchanged from the Claude
Code skill and from the deployed HF Space:

  AUTORUBRIC_JUDGES   comma-separated LiteLLM model ids. >=2 enables ensemble +
                      inter-judge reliability (Cohen's kappa / agreement).
                      Default: a single cheap Anthropic judge.
  OPENROUTER_API_KEY  read automatically by LiteLLM for the openrouter/ prefix.

Cross-family ensemble (recommended for the reliability story, and the honest fix
for self-preference since a non-Anthropic judge grades the Anthropic-written v2):
  export AUTORUBRIC_JUDGES="openrouter/anthropic/claude-haiku-4-5,openrouter/google/gemini-2.5-flash"
"""

from __future__ import annotations

import os

# Single default judge — confirmed working against OpenRouter in the Phase 0 spike.
DEFAULT_JUDGE = "openrouter/anthropic/claude-haiku-4-5"


def judge_models() -> list[str]:
    raw = os.environ.get("AUTORUBRIC_JUDGES", "").strip()
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    return [DEFAULT_JUDGE]


# Domain rule carried over from the old rubric: briefs without state.json access
# (v1, general) cannot express cross-session trend depth, so this dimension is
# capped regardless of prose quality.
TREND_DIMENSION_ID = "trend_continuity"
TREND_CAP_FOR_STATELESS = 2

# Same aggregation as the OLD framework, so final scores are directly comparable.
# The ONLY methodological change is how the 60% LLM portion is produced.
AUTO_WEIGHT = 0.40   # deterministic regex structural checks
LLM_WEIGHT = 0.60    # AutoRubric normalized weighted score (atomic per-criterion)

# The mandate context every judge grades against (the brief's implicit "query").
QUERY = (
    "This is the Emirates Development Bank (EDB) daily macro intelligence brief. "
    "EDB is a government-owned development finance institution pursuing Operation "
    "300bn (grow industrial GDP to AED 300bn by 2031) across five priority sectors: "
    "advanced technology, manufacturing, healthcare, renewables, food security. "
    "The AED is pegged to USD at 3.6725, so US rate moves transmit via CBUAE -> "
    "EIBOR -> EDB's floating-rate SME portfolio. Grade the brief as a specialist "
    "macro-credit analyst would: reward specific, sourced, sector-mapped, "
    "quantified analysis and penalise generic commentary or undisclosed estimates."
)
