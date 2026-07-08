# AutoRubric Evaluation Framework (EDB briefs)

A second, independent evaluation framework for the EDB macro briefs, built on
[AutoRubric](https://autorubric.org) (Rao & Callison-Burch). It runs **side by
side** with the legacy `eval/` framework — nothing in `eval/` is modified — so the
two can be compared directly.

## Why a second framework

The legacy evaluator scores all 7 quality dimensions for all 3 briefs in **one
LLM call**. That invites the *halo effect / criterion conflation* the AutoRubric
paper is built against: a polished-looking brief gets uniformly high marks. This
framework judges **each criterion in its own LLM call** (atomic decomposition),
adds **negative penalty criteria** for anti-patterns, and supports **ensemble
judging with inter-judge reliability** (Cohen's κ / agreement).

## What it scores

Same aggregation as legacy so final scores are comparable (`0–100`):

- **40% structural** — the same 20 deterministic regex checks (`structural.py`,
  reusing `eval/rubric.py`). Format compliance is a job for regex, not an LLM.
- **60% LLM** — AutoRubric normalized weighted score over:
  - **7 ordinal dimensions** (1–5, behavioural anchors, imported verbatim from
    `eval/rubric.py` so both frameworks judge the same constructs). Ordinal
    options use *descriptive* labels (`exemplary`…`absent`), never `"1"–"5"`,
    to avoid colliding with the judge's shuffled option positions.
  - **3 negative penalties** (`generic_market_commentary`,
    `silent_stale_or_estimated_data`, `unsupported_number`) — anti-patterns the
    legacy rubric could not express. Negative weights counter LLM leniency bias.

`trend_continuity` is capped at 2 for stateless (v1 / general) briefs, matching
the legacy domain rule.

## Files

| File | Role |
|------|------|
| `config.py`      | judges (env `AUTORUBRIC_JUDGES`), weights, mandate query |
| `rubric_def.py`  | builds the AutoRubric `Rubric` (7 ordinal + 3 penalties) |
| `structural.py`  | the shared 20-check deterministic layer |
| `runner.py`      | core async engine: grade one/many briefs, reliability, scoring |
| `report.py`      | renders the markdown 3-way comparison report |
| `run_eval.py`    | CLI entrypoint (used by the skill) + `state.json` persistence |
| `spike.py`       | Phase 0 proof-of-concept (toy rubric) |
| `compare.py`     | controlled OLD-vs-NEW head-to-head on one brief |

## Running it

### As a Claude Code skill
```
/eval-brief-autorubric
```
Runs `run_eval.py`, interprets the report, and patches `CLAUDE.md` for any v2
dimension ≤ 3 or fired penalty (AutoRubric §5 "skill improvement" loop).

### From the CLI
```bash
venv/bin/python -m eval_autorubric.run_eval            # single judge
venv/bin/python -m eval_autorubric.compare             # OLD vs NEW on one brief
```

### On the deployed HF Space
Tab **🧪 AutoRubric Eval** — one button; fetches the latest briefs, grades,
commits `outputs/eval_autorubric_<date>.md`, and appends to
`state.json → autorubric_eval_history`.

## Ensemble + reliability (recommended for presentations)

A single judge gives no reliability signal. Set 2+ **cross-family** judges to
enable inter-judge agreement (and to fix self-preference — a non-Anthropic judge
grading the Anthropic-written v2):

```bash
export AUTORUBRIC_JUDGES="openrouter/anthropic/claude-haiku-4-5,openrouter/google/gemini-2.5-flash"
```

On HF, set `AUTORUBRIC_JUDGES` as a Space secret. Requires `OPENROUTER_API_KEY`.

## State separation

Results go to `state.json → autorubric_eval_history`, kept entirely separate from
the legacy `eval_history`, so both frameworks accumulate independent longitudinal
records for comparison.
