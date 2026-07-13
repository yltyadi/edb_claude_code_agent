# EDB Agent Evaluation Report — AutoRubric Framework
**Date:** 2026-07-13
**Framework:** AutoRubric (analytic rubric, atomic per-criterion judging)
**v2 brief:** brief_v2_2026-07-13_0843.md
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
| peg_chain_traced                 | +0.08 | ❌ | ❌ | ❌ |
| watch_list_specific              | +0.07 | ✅ | ✅ | ❌ |
| action_flag_with_rationale       | +0.07 | ✅ | ✅ | ❌ |
| calculation_block_aed            | +0.06 | ✅ | ✅ | ❌ |
| header_metadata_complete         | +0.05 | ✅ | ✅ | ❌ |
| prior_state_referenced           | +0.05 | ✅ | ❌ | ❌ |

## 2 — Ordinal Quality Dimensions (1–5, atomic per-criterion judging)

| Dimension | Wt | v2 Agent | v1 Agent | General LLM |
|-----------|:--:|:--:|:--:|:--:|
| Mandate Relevance                    | 20% | 5/5 | 5/5 | 2/5 |
| Data Grounding & Source Citation     | 16% | 4/5 | 3/5 | 3/5 |
| Quantitative Accuracy & Calculation Discipline | 16% | 4/5 | 5/5 | 1/5 |
| Output Structure Completeness        | 12% | 3/5 | 5/5 | 4/5 |
| Action Specificity                   | 12% | 5/5 | 4/5 | 1/5 |
| Data Integrity & Gap Disclosure      | 12% | 5/5 | 4/5 | 3/5 |
| Trend & Continuity                   | 12% | 5/5 | 3/5 | 2/5 |

## 3 — Negative Penalties (anti-patterns — MET is bad)

| Penalty | Wt | v2 Agent | v1 Agent | General LLM |
|---------|:--:|:--:|:--:|:--:|
| generic_market_commentary        | -0.06 | ok | ok | ok |
| silent_stale_or_estimated_data   | -0.10 | ⚠️ MET | ⚠️ MET | ok |
| unsupported_number               | -0.15 | ok | ⚠️ MET | ⚠️ MET |

## Reliability

Ensemble of 2 judges (claude-haiku-4-5, gemini-2.5-flash), majority vote.

- **v2 Agent**: mean inter-judge agreement 0.85
- **v1 Agent**: mean inter-judge agreement 0.75
- **General LLM**: mean inter-judge agreement 0.70

---

## Final Scores

| | v2 Agent | v1 Agent | General LLM |
|--|:--:|:--:|:--:|
| AutoRubric result.score        | 0.818 | 0.670 | 0.091 |
| **Final Score / 100**          | **81.8** | **67.0** | **9.1** |

- **v2 vs v1**: +14.8 pts
- **v2 vs General**: +72.7 pts
- **v1 vs General**: +58.0 pts

**Token usage:** v2 Agent: 279663 / v1 Agent: 199359 / General LLM: 175673

---

## v2 Improvement Targets

- **peg_chain_traced** (FAIL): While the submission contains extensive analysis of EIBOR, the CBUAE base rate, and EDB's floating-rate SME loan portfolio, it does NOT explicitly trace the transmission chain starting from a Federal 
- **Output Structure Completeness** (3/5): The submission exemplifies all three required types with complete substantive detail: Type A includes a detailed headline with escalation context, a comprehensive 5-row sector matrix with quantified d
- **penalty: silent_stale_or_estimated_data**: The submission uses EIBOR 3M at 3.900% in multiple calculations (loan ADS scenarios, reference rate structure) without explicitly disclosing at the point of use that this is an estimated figure. While
