# EDB Agent Evaluation Report — AutoRubric Framework
**Date:** 2026-07-14
**Framework:** AutoRubric (analytic rubric, atomic per-criterion judging)
**v2 brief:** brief_v2_2026-07-14_1030.md
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
| Data Grounding & Source Citation     | 16% | 5/5 | 3/5 | 4/5 |
| Quantitative Accuracy & Calculation Discipline | 16% | 5/5 | 4/5 | 1/5 |
| Output Structure Completeness        | 12% | 3/5 | 4/5 | 3/5 |
| Action Specificity                   | 12% | 3/5 | 4/5 | 1/5 |
| Data Integrity & Gap Disclosure      | 12% | 3/5 | 3/5 | 1/5 |
| Trend & Continuity                   | 12% | 5/5 | 3/5 | 3/5 |

## 3 — Negative Penalties (anti-patterns — MET is bad)

| Penalty | Wt | v2 Agent | v1 Agent | General LLM |
|---------|:--:|:--:|:--:|:--:|
| generic_market_commentary        | -0.06 | ok | ok | ok |
| silent_stale_or_estimated_data   | -0.10 | ⚠️ MET | ⚠️ MET | ok |
| unsupported_number               | -0.15 | ⚠️ MET | ⚠️ MET | ⚠️ MET |

## Reliability

Ensemble of 2 judges (claude-haiku-4-5, gemini-2.5-flash), majority vote.

- **v2 Agent**: mean inter-judge agreement 0.80
- **v1 Agent**: mean inter-judge agreement 0.75
- **General LLM**: mean inter-judge agreement 0.72

---

## Final Scores

| | v2 Agent | v1 Agent | General LLM |
|--|:--:|:--:|:--:|
| AutoRubric result.score        | 0.756 | 0.614 | 0.136 |
| **Final Score / 100**          | **75.6** | **61.4** | **13.6** |

- **v2 vs v1**: +14.2 pts
- **v2 vs General**: +61.9 pts
- **v1 vs General**: +47.7 pts

**Token usage:** v2 Agent: 265032 / v1 Agent: 199432 / General LLM: 179671

---

## v2 Improvement Targets

- **Output Structure Completeness** (3/5): The submission exemplifies all three required types with comprehensive, substantive completion: Type A includes a detailed headline with sector matrix (5 rows with quantified impacts), key number in A
- **Action Specificity** (3/5): The submission exemplifies the behavioral anchor at 5/5: every action flag names a specific team (Credit Risk), concrete threshold (DSCR <1.10×, Brent $87/bbl, 8× war-risk insurance for 90 days), and 
- **Data Integrity & Gap Disclosure** (3/5): This submission exemplifies the highest standard of disclosure and transparency. Every calculation input is explicitly labeled with its source, vintage, and estimation method: EIBOR is marked '(est.)'
- **penalty: silent_stale_or_estimated_data**: The submission uses EIBOR as an estimated rate in calculations WITHOUT consistently disclosing it as estimated at every point of use. While the methodology section states 'All EIBOR figures tagged (es
- **penalty: unsupported_number**: The brief contains multiple material quantitative figures that cannot be traced to named sources or shown calculations. Most notably: (1) 'AED +89.3bn/yr uplift in UAE oil fiscal revenue' — while a ca
