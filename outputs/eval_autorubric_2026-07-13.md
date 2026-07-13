# EDB Agent Evaluation Report — AutoRubric Framework
**Date:** 2026-07-13
**Framework:** AutoRubric (analytic rubric, atomic per-criterion judging)
**v2 brief:** brief_v2_2026-07-13_0905.md
**v1 brief:** brief_v1_2026-07-13_0853.md
**General brief:** brief_general_2026-06-17.md
**Judges:** openrouter/anthropic/claude-haiku-4-5, openrouter/google/gemini-2.5-flash

---

## 1 — Binary Structural Requirements (✅ = MET, ❌ = FAIL)

| Requirement | Wt | v2 Agent | v1 Agent | General LLM |
|-------------|:--:|:--:|:--:|:--:|
| sections_complete                | +0.10 | ✅ | ✅ | ❌ |
| sector_matrix_complete           | +0.10 | ✅ | ✅ | ❌ |
| required_calculations_present    | +0.10 | ✅ | ✅ | ❌ |
| sources_with_vintage_dates       | +0.08 | ✅ | ✅ | ❌ |
| peg_chain_traced                 | +0.08 | ✅ | ❌ | ❌ |
| watch_list_specific              | +0.07 | ✅ | ✅ | ❌ |
| action_flag_with_rationale       | +0.07 | ✅ | ✅ | ❌ |
| calculation_block_aed            | +0.06 | ✅ | ✅ | ❌ |
| header_metadata_complete         | +0.05 | ✅ | ✅ | ❌ |
| prior_state_referenced           | +0.05 | ✅ | ❌ | ❌ |

## 2 — Ordinal Quality Dimensions (1–5, atomic per-criterion judging)

| Dimension | Wt | v2 Agent | v1 Agent | General LLM |
|-----------|:--:|:--:|:--:|:--:|
| Mandate Relevance                    | 20% | 5/5 | 5/5 | 4/5 |
| Data Grounding & Source Citation     | 16% | 5/5 | 4/5 | 3/5 |
| Quantitative Accuracy & Calculation Discipline | 16% | 5/5 | 4/5 | 1/5 |
| Output Structure Completeness        | 12% | 4/5 | 5/5 | 3/5 |
| Action Specificity                   | 12% | 3/5 | 5/5 | 1/5 |
| Data Integrity & Gap Disclosure      | 12% | 5/5 | 4/5 | 1/5 |
| Trend & Continuity                   | 12% | 5/5 | 3/5 | 2/5 |

## 3 — Negative Penalties (anti-patterns — MET is bad)

| Penalty | Wt | v2 Agent | v1 Agent | General LLM |
|---------|:--:|:--:|:--:|:--:|
| generic_market_commentary        | -0.06 | ok | ok | ok |
| silent_stale_or_estimated_data   | -0.10 | ok | ⚠️ MET | ok |
| unsupported_number               | -0.15 | ⚠️ MET | ⚠️ MET | ⚠️ MET |

## Reliability

Ensemble of 2 judges (claude-haiku-4-5, gemini-2.5-flash), majority vote.

- **v2 Agent**: mean inter-judge agreement 0.88
- **v1 Agent**: mean inter-judge agreement 0.75
- **General LLM**: mean inter-judge agreement 0.78

---

## Final Scores

| | v2 Agent | v1 Agent | General LLM |
|--|:--:|:--:|:--:|
| AutoRubric result.score        | 0.864 | 0.688 | 0.097 |
| **Final Score / 100**          | **86.4** | **68.8** | **9.7** |

- **v2 vs v1**: +17.6 pts
- **v2 vs General**: +76.7 pts
- **v1 vs General**: +59.1 pts

**Token usage:** v2 Agent: 344524 / v1 Agent: 199294 / General LLM: 179676

---

## v2 Improvement Targets

- **Action Specificity** (3/5): The submission is entirely absent of action flags (MONITOR/REVIEW/ESCALATE) with the required structure of specific team/portfolio segment, concrete trigger condition/threshold, and reassessment miles
- **penalty: unsupported_number**: The submission contains multiple material quantitative figures that cannot be traced to named sources or shown calculations. Most notably: (1) UAE fiscal breakeven of ~$55.00/bbl is attributed to 'IMF
