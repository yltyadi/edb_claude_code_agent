# EDB Agent Evaluation Report — AutoRubric Framework
**Date:** 2026-07-09
**Framework:** AutoRubric (analytic rubric, atomic per-criterion judging)
**v2 brief:** brief_v2_2026-07-06_1209.md
**v1 brief:** brief_v1_2026-06-17_0700.md
**General brief:** brief_general_2026-06-17.md
**Judges:** openrouter/anthropic/claude-haiku-4-5, openrouter/google/gemini-2.5-flash
**Aggregation:** structural 40% (deterministic) + LLM 60% (AutoRubric normalized)

---

## LLM Quality Dimensions — atomic per-criterion (1–5)

| Dimension | Wt | v2 Agent | v1 Agent | General |
|-----------|:--:|:--:|:--:|:--:|
| Mandate Relevance            | 20% | 5/5 | 5/5 | 3/5 |
| Data Grounding & Source Citation | 16% | 5/5 | 4/5 | 4/5 |
| Quantitative Accuracy & Calculation Discipline | 16% | 5/5 | 5/5 | 1/5 |
| Output Structure Completeness | 12% | 3/5 | 4/5 | 4/5 |
| Action Specificity           | 12% | 5/5 | 4/5 | 1/5 |
| Data Integrity & Gap Disclosure | 12% | 5/5 | 5/5 | 2/5 |
| Trend & Continuity           | 12% | 4/5 | 3/5 | 2/5 |

## Negative Penalties (anti-patterns — MET is bad)

| Penalty | Wt | v2 Agent | v1 Agent | General |
|---------|:--:|:--:|:--:|:--:|
| generic_market_commentary        | -0.06 | ok | ok | ok |
| silent_stale_or_estimated_data   | -0.10 | ok | ok | ok |
| unsupported_number               | -0.15 | ok | ok | ⚠️ MET |

## Reliability

Ensemble of 2 judges (claude-haiku-4-5, gemini-2.5-flash), majority vote. Mean inter-judge agreement per brief (reliability indicator — low values flag criteria to route to human review):

- **v2 Agent**: mean inter-judge agreement 0.85
- **v1 Agent**: mean inter-judge agreement 0.80
- **General**: mean inter-judge agreement 0.70

---

## Final Scores

| | v2 Agent | v1 Agent | General |
|--|:--:|:--:|:--:|
| Structural (of 20)         | 18/20 | 18/20 | 5/20 |
| LLM score (norm 0–1)       | 0.910 | 0.840 | 0.220 |
| **Final Score / 100**      | **90.6** | **86.4** | **23.2** |

- **v2 vs v1**: +4.2 pts
- **v2 vs General**: +67.4 pts
- **v1 vs General**: +63.2 pts

**Token usage:** v2 Agent: 200308 / v1 Agent: 122127 / General: 90368

---

## v2 Improvement Targets (dimensions ≤ 3 or penalties fired)

- **Output Structure Completeness** (3/5): The submission exemplifies all three required types with substantive, complete sub-fields: Type A presents five data-justified macro signals (US Treasury, Brent, Fed Funds, Industrial Production, UAE 
