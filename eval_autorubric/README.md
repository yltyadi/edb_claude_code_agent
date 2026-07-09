# AutoRubric Evaluation Framework (EDB briefs)

A second, independent evaluation framework for the EDB macro briefs, built on
[AutoRubric](https://autorubric.org) (Rao & Callison-Burch, UPenn/DARPA). It runs
**side by side** with the legacy `eval/` framework — nothing in `eval/` is touched —
so the two can be compared directly in a presentation.

## Why a second framework

The legacy evaluator scores all 7 quality dimensions in **one LLM call**. That invites
the *halo effect / criterion conflation* the AutoRubric paper is built against: a
polished-looking brief gets uniformly high marks because quality impressions bleed across
dimensions. This framework judges **each criterion in its own LLM call** (atomic
decomposition), adds **negative penalty criteria** for anti-patterns, and uses a
**2-model cross-family ensemble** for inter-judge reliability.

## Paper API used (Listings 1–4)

```python
# Listing 2: ordinal criterion with plain-dict options
from autorubric import Rubric, Criterion

rubric = Rubric([
    Criterion(
        weight=10.0,
        requirement="Rate the clarity of explanation",
        scale_type="ordinal",
        options=[
            {"label": "Absent",    "value": 0.00},
            {"label": "Weak",      "value": 0.25},
            {"label": "Adequate",  "value": 0.50},
            {"label": "Strong",    "value": 0.75},
            {"label": "Exemplary", "value": 1.00},
        ],
    ),
    # Listing 3: negative binary criterion (penalty when anti-pattern is MET)
    Criterion(weight=-0.15, requirement="Contains unsupported quantitative claims"),
])

# Listing 4: 2-model cross-family ensemble
from autorubric import LLMConfig
from autorubric.graders import CriterionGrader, JudgeSpec

grader = CriterionGrader(
    judges=[
        JudgeSpec(LLMConfig(model="openrouter/anthropic/claude-haiku-4-5"), "haiku",   weight=1.0),
        JudgeSpec(LLMConfig(model="openrouter/google/gemini-2.5-flash"),    "gemini",  weight=1.0),
    ],
    aggregation="majority",
)
result = await rubric.grade(to_grade=brief_text, grader=grader, query=mandate_context)
print(f"Score: {result.score:.2f}, Agreement: {result.mean_agreement:.1%}")
```

## What it scores

Same 0–100 aggregation as the legacy framework for fair comparison:

- **40% structural** — 20 deterministic regex checks (reusing `eval/rubric.py`)
- **60% LLM** — `result.score` from AutoRubric (normalized weighted score) over:
  - **7 ordinal dimensions** (5-level, behavioural anchors, same constructs as legacy)
  - **3 negative penalty criteria** (binary, fire when anti-pattern is present)

## Files

| File | Role |
|------|------|
| `config.py`      | 2-model ensemble default, weights, mandate query |
| `rubric_def.py`  | `Rubric([Criterion(...)])` — paper Listing 2–3 |
| `structural.py`  | shared 20-check deterministic layer |
| `runner.py`      | `result.score` + `result.mean_agreement` — paper Listing 4 |
| `report.py`      | 3-way comparison markdown report |
| `run_eval.py`    | CLI entrypoint + `state.json → autorubric_eval_history` |
| `compare.py`     | OLD (conflated) vs NEW (atomic) head-to-head on one brief |
| `spike.py`       | Phase 0 proof-of-concept |

## Running it

### Claude Code skill
```
/eval-brief-autorubric
```

### CLI
```bash
venv/bin/python -m eval_autorubric.run_eval          # default 2-model ensemble
venv/bin/python -m eval_autorubric.compare           # OLD vs NEW head-to-head
```

### HF Space
Tab **🧪 AutoRubric Eval** — fetches latest briefs, grades with 2-model ensemble,
commits `outputs/eval_autorubric_<date>.md`, appends to `state.json → autorubric_eval_history`.

## Overriding judges

```bash
# 3-judge cross-family ensemble
export AUTORUBRIC_JUDGES="openrouter/anthropic/claude-haiku-4-5,openrouter/google/gemini-2.5-flash,openrouter/openai/gpt-4.1-mini"
```

On HF Space, set `AUTORUBRIC_JUDGES` as a Space secret. Requires `OPENROUTER_API_KEY`.

## State separation

Results go to `state.json → autorubric_eval_history`, kept entirely separate from
the legacy `eval_history`, so both frameworks accumulate independent longitudinal
records.
