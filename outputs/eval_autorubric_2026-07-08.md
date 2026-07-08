# EDB Agent Evaluation Report — AutoRubric Framework
**Date:** 2026-07-08
**Framework:** AutoRubric (analytic rubric, atomic per-criterion judging)
**v2 brief:** brief_v2_2026-07-06_1209.md
**v1 brief:** brief_v1_2026-06-17_0700.md
**General brief:** brief_general_2026-06-17.md
**Judges:** openrouter/anthropic/claude-haiku-4-5
**Aggregation:** structural 40% (deterministic) + LLM 60% (AutoRubric normalized)

---

## LLM Quality Dimensions — atomic per-criterion (1–5)

| Dimension | Wt | v2 Agent | v1 Agent | General |
|-----------|:--:|:--:|:--:|:--:|
| Mandate Relevance            | 20% | 5/5 | 5/5 | 3/5 |
| Data Grounding & Source Citation | 16% | 5/5 | 5/5 | 1/5 |
| Quantitative Accuracy & Calculation Discipline | 16% | 4/5 | 5/5 | 1/5 |
| Output Structure Completeness | 12% | 4/5 | 5/5 | 2/5 |
| Action Specificity           | 12% | 5/5 | 4/5 | 1/5 |
| Data Integrity & Gap Disclosure | 12% | 5/5 | 4/5 | 2/5 |
| Trend & Continuity           | 12% | 5/5 | 2/5 | 2/5 |

## Negative Penalties (anti-patterns — MET is bad)

| Penalty | Wt | v2 Agent | v1 Agent | General |
|---------|:--:|:--:|:--:|:--:|
| generic_market_commentary        | -8 | ok | ok | ok |
| silent_stale_or_estimated_data   | -10 | ⚠️ MET | ⚠️ MET | ok |
| unsupported_number               | -12 | ok | ⚠️ MET | ok |

## Reliability

Single judge (`claude-haiku-4-5`). No inter-judge reliability signal — set `AUTORUBRIC_JUDGES` to 2+ models (ideally cross-family) to enable Cohen's κ / agreement.

---

## Final Scores

| | v2 Agent | v1 Agent | General |
|--|:--:|:--:|:--:|
| Structural (of 20)         | 18/20 | 18/20 | 5/20 |
| LLM score (norm 0–1)       | 0.830 | 0.630 | 0.190 |
| **Final Score / 100**      | **85.8** | **73.8** | **21.4** |

- **v2 vs v1**: +12.0 pts
- **v2 vs General**: +64.4 pts
- **v1 vs General**: +52.4 pts

**Token usage:** v2 Agent: 103878 / v1 Agent: 64612 / General: 48162

---

## v2 Improvement Targets (dimensions ≤ 3 or penalties fired)

- **penalty fired: silent_stale_or_estimated_data**: The submission uses EIBOR 3.8155% as an estimated rate in multiple calculations (Calculation 1: DSCR sensitivity, Step 3 calculations, and Type C stakeholder bulletin) WITHOUT disclosing the estimate 
