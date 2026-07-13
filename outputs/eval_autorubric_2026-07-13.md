# EDB Agent Evaluation Report — AutoRubric Framework
**Date:** 2026-07-13
**Framework:** AutoRubric (analytic rubric, atomic per-criterion judging)
**v2 brief:** brief_v2_2026-07-13_0820.md
**v1 brief:** brief_v1_2026-06-17_0700.md
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
| peg_chain_traced                 | +0.08 | ✅ | ✅ | ❌ |
| watch_list_specific              | +0.07 | ✅ | ✅ | ❌ |
| action_flag_with_rationale       | +0.07 | ❌ | ✅ | ❌ |
| calculation_block_aed            | +0.06 | ✅ | ✅ | ❌ |
| header_metadata_complete         | +0.05 | ✅ | ✅ | ❌ |
| prior_state_referenced           | +0.05 | ✅ | ✅ | ❌ |

## 2 — Ordinal Quality Dimensions (1–5, atomic per-criterion judging)

| Dimension | Wt | v2 Agent | v1 Agent | General LLM |
|-----------|:--:|:--:|:--:|:--:|
| Mandate Relevance                    | 20% | 5/5 | 5/5 | 3/5 |
| Data Grounding & Source Citation     | 16% | 3/5 | 4/5 | 3/5 |
| Quantitative Accuracy & Calculation Discipline | 16% | 5/5 | 4/5 | 2/5 |
| Output Structure Completeness        | 12% | 5/5 | 5/5 | 3/5 |
| Action Specificity                   | 12% | 5/5 | 3/5 | 1/5 |
| Data Integrity & Gap Disclosure      | 12% | 5/5 | 5/5 | 4/5 |
| Trend & Continuity                   | 12% | 5/5 | 3/5 | 2/5 |

## 3 — Negative Penalties (anti-patterns — MET is bad)

| Penalty | Wt | v2 Agent | v1 Agent | General LLM |
|---------|:--:|:--:|:--:|:--:|
| generic_market_commentary        | -0.06 | ok | ok | ok |
| silent_stale_or_estimated_data   | -0.10 | ok | ok | ok |
| unsupported_number               | -0.15 | ⚠️ MET | ok | ⚠️ MET |

## Reliability

Ensemble of 2 judges (claude-haiku-4-5, gemini-2.5-flash), majority vote.

- **v2 Agent**: mean inter-judge agreement 0.90
- **v1 Agent**: mean inter-judge agreement 0.82
- **General LLM**: mean inter-judge agreement 0.70

---

## Final Scores

| | v2 Agent | v1 Agent | General LLM |
|--|:--:|:--:|:--:|
| AutoRubric result.score        | 0.830 | 0.886 | 0.142 |
| **Final Score / 100**          | **83.0** | **88.6** | **14.2** |

- **v2 vs v1**: -5.7 pts
- **v2 vs General**: +68.8 pts
- **v1 vs General**: +74.4 pts

**Token usage:** v2 Agent: 383161 / v1 Agent: 243191 / General LLM: 179784

---

## v2 Improvement Targets

- **action_flag_with_rationale** (FAIL): The submission contains no explicit action flags (MONITOR, REVIEW, or ESCALATE) with specific, evidence-based rationale tied to named EDB portfolio exposures, sector mandates, or thresholds. While the
- **Data Grounding & Source Citation** (3/5): This submission exemplifies the sourcing standard. Every material number is traced to a named authority: CBUAE base rate (3.65%, confirmed July 13), EIBOR 3M (3.900%, July 10 CBUAE tool), Brent ($79.1
- **penalty: unsupported_number**: The brief contains multiple material quantitative figures that cannot be traced to named sources or shown calculations. Most notably: (1) The 60% petrochemical feedstock pass-through rate in Calculati
