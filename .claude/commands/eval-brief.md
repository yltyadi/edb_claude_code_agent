You are evaluating three macro intelligence briefs for Emirates Development Bank and producing a scored 3-way comparison report. After scoring, you will patch CLAUDE.md with improvement instructions for any v2 dimension scoring ≤ 3, and update state.json with the eval results.

The three agents being compared:
- **General** — baseline Claude with web search, no EDB tools or format
- **v1** — EDB-specialised pipeline (signal scoring, sector matrix, EIBOR calc) but no cross-session memory
- **v2** — v1 plus state.json memory, streak language, version header, and CLAUDE.md feedback loop

---

## Step 1 — Locate all three briefs

```bash
ls -t outputs/brief_v2*.md | head -3
ls -t outputs/brief_v1*.md | head -3
ls -t outputs/brief_general*.md | head -3
```

Pick the most recent of each type. If any is missing, note the gap and evaluate only what exists.

---

## Step 2 — Run automated checks on all three

```bash
python3 eval/check.py <v2_brief_path>
python3 eval/check.py <v1_brief_path>
python3 eval/check.py <general_brief_path>
```

Record exact pass/fail for all 20 checks per brief.

---

## Step 3 — Read everything needed for scoring

Use the Read tool to read:
1. The v2 brief in full
2. The v1 brief in full
3. The general brief in full
4. `eval/rubric.py` — for the 7 dimension definitions and scoring scales
5. `outputs/state.json` — for eval_history context and prior scores

---

## Step 4 — Score all 7 LLM dimensions for all three briefs (YOU are the judge)

For each dimension, score all three briefs 1–5 using the criteria in rubric.py.
Write 1–2 sentences of reasoning per brief per dimension. Be direct and specific —
name the exact gap or strength that drove the score.

| # | Dimension | Weight |
|---|-----------|--------|
| 1 | Mandate Relevance | 20% |
| 2 | Data Grounding & Source Citation | 16% |
| 3 | Quantitative Accuracy | 16% |
| 4 | Output Structure Completeness | 12% |
| 5 | Action Specificity | 12% |
| 6 | Data Integrity & Gap Disclosure | 12% |
| 7 | Trend & Continuity | 12% |

**Note on Trend & Continuity:**
- General brief: structurally capped at 2/5 (no state.json access)
- v1 brief: structurally capped at 2/5 (no state.json access)
- v2 brief: can score up to 5/5 (reads state.json, uses streak data)

---

## Step 5 — Compute final scores for all three

Run this in Python to be exact:

```bash
python3 - <<'EOF'
dims = [
    ("Mandate Relevance",    0.20, <v2>, <v1>, <gen>),
    ("Data Grounding",       0.16, <v2>, <v1>, <gen>),
    ("Quant Accuracy",       0.16, <v2>, <v1>, <gen>),
    ("Structure Complete",   0.12, <v2>, <v1>, <gen>),
    ("Action Specificity",   0.12, <v2>, <v1>, <gen>),
    ("Data Integrity",       0.12, <v2>, <v1>, <gen>),
    ("Trend & Continuity",   0.12, <v2>, <v1>, <gen>),
]
for label, w, v2, v1, gen in dims:
    print(f"{label:<24} v2 {v2}/5  v1 {v1}/5  GEN {gen}/5  (wt {w*100:.0f}%)")
v2_llm  = sum(v2*w  for _,w,v2,_,_  in dims) / 5
v1_llm  = sum(v1*w  for _,w,_,v1,_  in dims) / 5
gen_llm = sum(gen*w for _,w,_,_,gen in dims) / 5
v2_auto  = <v2_passed>  / 20
v1_auto  = <v1_passed>  / 20
gen_auto = <gen_passed> / 20
v2_final  = (v2_auto  * 0.40 + v2_llm  * 0.60) * 100
v1_final  = (v1_auto  * 0.40 + v1_llm  * 0.60) * 100
gen_final = (gen_auto * 0.40 + gen_llm * 0.60) * 100
print(f"\nv2 final:  {v2_final:.1f}/100")
print(f"v1 final:  {v1_final:.1f}/100")
print(f"gen final: {gen_final:.1f}/100")
print(f"v2 vs v1:  {v2_final-v1_final:+.1f}  |  v2 vs gen: {v2_final-gen_final:+.1f}  |  v1 vs gen: {v1_final-gen_final:+.1f}")
EOF
```

---

## Step 6 — Output the 3-way comparison report

```
# EDB Agent Evaluation Report — 3-Way Comparison
**Date:** <today>
**v2 brief:** <path>
**v1 brief:** <path>
**General brief:** <path>
**Rubric version:** v2 (20 automated checks, 7 LLM dimensions)

## Automated Checks (40% of score)
| Check | v2 Agent | v1 Agent | General |
|-------|:--------:|:--------:|:-------:|
| Executive Brief (Type A) present            | ✓/✗ | ✓/✗ | ✓/✗ |
| Credit Alert (Type B) present               | ✓/✗ | ✓/✗ | ✓/✗ |
| Stakeholder Bulletin (Type C) present       | ✓/✗ | ✓/✗ | ✓/✗ |
| Sector matrix (all 5 sectors)               | ✓/✗ | ✓/✗ | ✓/✗ |
| Key number field present                    | ✓/✗ | ✓/✗ | ✓/✗ |
| Watch list present                          | ✓/✗ | ✓/✗ | ✓/✗ |
| Action flag (MONITOR/REVIEW/ESCALATE)       | ✓/✗ | ✓/✗ | ✓/✗ |
| Calculation block with AED                  | ✓/✗ | ✓/✗ | ✓/✗ |
| EIBOR ±25bps scenario                       | ✓/✗ | ✓/✗ | ✓/✗ |
| Oil revenue / fiscal impact calc            | ✓/✗ | ✓/✗ | ✓/✗ |
| Sources section present                     | ✓/✗ | ✓/✗ | ✓/✗ |
| Methodology / data-gap note                 | ✓/✗ | ✓/✗ | ✓/✗ |
| EIBOR explicitly mentioned                  | ✓/✗ | ✓/✗ | ✓/✗ |
| Full peg chain traced                       | ✓/✗ | ✓/✗ | ✓/✗ |
| Date header present                         | ✓/✗ | ✓/✗ | ✓/✗ |
| Signals processed count in header           | ✓/✗ | ✓/✗ | ✓/✗ |
| Dual-scenario analysis                      | ✓/✗ | ✓/✗ | ✓/✗ |
| Operation 300bn progress computed           | ✓/✗ | ✓/✗ | ✓/✗ |
| Prior-run baseline / streak reference       | ✓/✗ | ✓/✗ | ✓/✗ |
| Agent version header                        | ✓/✗ | ✓/✗ | ✓/✗ |
| **TOTAL**                                   | **X/20** | **X/20** | **X/20** |

## LLM Dimensions (60% of score)
| Dimension | Wt | v2 | v1 | General |
|-----------|:--:|:--:|:--:|:-------:|
| Mandate Relevance       | 20% | X/5 | X/5 | X/5 |
| Data Grounding          | 16% | X/5 | X/5 | X/5 |
| Quantitative Accuracy   | 16% | X/5 | X/5 | X/5 |
| Structure Completeness  | 12% | X/5 | X/5 | X/5 |
| Action Specificity      | 12% | X/5 | X/5 | X/5 |
| Data Integrity          | 12% | X/5 | X/5 | X/5 |
| Trend & Continuity      | 12% | X/5 | X/5 | X/5 |

### Reasoning
**{Dimension}**
- v2 Agent (N/5): ...
- v1 Agent (N/5): ...
- General Agent (N/5): ...

## Final Scores
|                        | v2 Agent | v1 Agent | General |
|------------------------|:--------:|:--------:|:-------:|
| Automated (40%)        | XX.X     | XX.X     | XX.X    |
| LLM Dimensions (60%)   | XX.X     | XX.X     | XX.X    |
| **Final Score**        | **XX.X / 100** | **XX.X / 100** | **XX.X / 100** |
| **v2 vs v1**           | **+XX.X pts**  |          |         |
| **v2 vs General**      | **+XX.X pts**  |          |         |
| **v1 vs General**      |          | **+XX.X pts** |        |

## Score Progression
[Brief note on what v1 gained over General, and what v2 gained over v1 — 2–3 sentences]

## Key Differentiators
[5–6 bullet points on what drove the gaps between each tier]

## Dimensions Needing Improvement (v2 Agent, scored ≤ 3)
[List each, with score and one-sentence diagnosis]
```

---

## Step 7 — Patch CLAUDE.md for low-scoring v2 dimensions

For every **v2 Agent** dimension scoring **≤ 3**, append a patch to the
`## Agent Improvement Notes` section of `CLAUDE.md`.

Read CLAUDE.md first, then append (do not overwrite existing notes):

```
### {YYYY-MM-DD} — {Dimension Name} (scored N/5)
- [Specific instruction #1: what to do differently, tied to the exact failure observed]
- [Specific instruction #2]
- [Specific instruction #3 if needed]
```

Be precise — reference the actual failure in today's v2 brief.

---

## Step 8 — Update state.json eval_history

Read `outputs/state.json`, add an entry to `eval_history`, and write it back:

```json
{
  "eval_date": "<today>",
  "v2_brief_path": "<path>",
  "v1_brief_path": "<path>",
  "general_brief_path": "<path>",
  "scores": {
    "v2": { "auto_passed": N, "auto_total": 20, "final_score": XX.X,
            "dimension_scores": { "mandate_relevance": N, "data_grounding": N,
              "quantitative_accuracy": N, "structure_completeness": N,
              "action_specificity": N, "data_integrity": N, "trend_continuity": N } },
    "v1": { "auto_passed": N, "auto_total": 20, "final_score": XX.X,
            "dimension_scores": { ... } },
    "general": { "auto_passed": N, "auto_total": 20, "final_score": XX.X,
                 "dimension_scores": { ... } }
  },
  "deltas": { "v2_vs_v1": XX.X, "v2_vs_gen": XX.X, "v1_vs_gen": XX.X },
  "dimensions_patched_v2": ["<dim_id>", ...]
}
```

---

## Step 9 — Save the report

Save to `outputs/eval_{YYYY-MM-DD}.md` using the Write tool.
If a file for today already exists, append `_v2` to the name (e.g. `outputs/eval_2026-06-17_v2.md`).
