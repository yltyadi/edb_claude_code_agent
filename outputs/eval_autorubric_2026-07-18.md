# EDB Agent Evaluation Report — AutoRubric Framework
**Date:** 2026-07-18
**Framework:** AutoRubric (analytic rubric, atomic per-criterion judging)
**v2 brief:** brief_v2_2026-07-18_0700.md
**v1 brief:** brief_v1_2026-07-14_1124.md
**General brief:** brief_general_2026-07-14.md
**Judges:** openrouter/anthropic/claude-haiku-4-5, openrouter/google/gemini-2.5-flash

---

## 1 — Binary Structural Requirements (✅ = MET, ❌ = FAIL)

| Requirement | Wt | v2 Agent | v1 Agent | General LLM |
|-------------|:--:|:--:|:--:|:--:|
| sections_complete                | +0.10 | ✅ | ✅ | ❌ |
| sector_matrix_complete           | +0.10 | ✅ | ✅ | ❌ |
| required_calculations_present    | +0.10 | ✅ | ✅ | ❌ |
| sources_with_vintage_dates       | +0.08 | ✅ | ✅ | ❌ |
| peg_chain_traced                 | +0.08 | ✅ | ✅ | ✅ |
| watch_list_specific              | +0.07 | ✅ | ✅ | ✅ |
| action_flag_with_rationale       | +0.07 | ✅ | ✅ | ❌ |
| calculation_block_aed            | +0.06 | ✅ | ✅ | ❌ |
| header_metadata_complete         | +0.05 | ✅ | ✅ | ❌ |
| prior_state_referenced           | +0.05 | ✅ | ❌ | ❌ |

## 2 — Ordinal Quality Dimensions (1–5, atomic per-criterion judging)

| Dimension | Wt | v2 Agent | v1 Agent | General LLM |
|-----------|:--:|:--:|:--:|:--:|
| Mandate Relevance                    | 20% | 5/5 | 5/5 | 2/5 |
| Data Grounding & Source Citation     | 16% | 5/5 | 5/5 | 5/5 |
| Quantitative Accuracy & Calculation Discipline | 16% | 5/5 | 5/5 | 1/5 |
| Output Structure Completeness        | 12% | 5/5 | 5/5 | 1/5 |
| Action Specificity                   | 12% | 4/5 | 4/5 | 1/5 |
| Data Integrity & Gap Disclosure      | 12% | 5/5 | 4/5 | 2/5 |
| Trend & Continuity                   | 12% | 3/5 | 3/5 | 2/5 |

## 3 — Negative Penalties (anti-patterns — MET is bad)

| Penalty | Wt | v2 Agent | v1 Agent | General LLM |
|---------|:--:|:--:|:--:|:--:|
| generic_market_commentary        | -0.06 | ok | ok | ok |
| silent_stale_or_estimated_data   | -0.10 | ⚠️ MET | ok | ok |
| unsupported_number               | -0.15 | ⚠️ MET | ok | ⚠️ MET |

## Reliability

Ensemble of 2 judges (claude-haiku-4-5, gemini-2.5-flash), majority vote.

- **v2 Agent**: mean inter-judge agreement 0.88
- **v1 Agent**: mean inter-judge agreement 0.93
- **General LLM**: mean inter-judge agreement 0.72

---

## Final Scores

| | v2 Agent | v1 Agent | General LLM |
|--|:--:|:--:|:--:|
| AutoRubric result.score        | 0.807 | 0.903 | 0.153 |
| **Final Score / 100**          | **80.7** | **90.3** | **15.3** |

- **v2 vs v1**: -9.7 pts
- **v2 vs General**: +65.3 pts
- **v1 vs General**: +75.0 pts

**Token usage:** v2 Agent: 262207 / v1 Agent: 228669 / General LLM: 175737

---

## v2 Improvement Targets

- **Trend & Continuity** (3/5): The brief exemplifies the 5/5 behavioral anchor: it provides multiple specific trend observations with numeric baselines from state.json (Fed 5th consecutive hold, EIBOR unchanged 11 consecutive days,
- **penalty: silent_stale_or_estimated_data**: The submission uses estimated EIBOR values (3.90%, marked as 'est.') in multiple calculations—including the peg transmission chain, DSCR sensitivity scenarios (+25bps, -25bps, -50bps), and the ADS fig
- **penalty: unsupported_number**: The brief contains multiple material quantitative figures that cannot be traced to named sources or shown calculations. Most notably: (1) The AED +94.44bn/yr war-premium uplift is stated as a 'Key num
