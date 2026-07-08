You are running the **AutoRubric** evaluation framework for the EDB macro briefs — the analytic, atomic-per-criterion evaluator (Rao & Callison-Burch, autorubric.org), kept side by side with the legacy `/eval-brief` framework so the two can be compared.

Unlike `/eval-brief`, you are **not** the judge here. Scoring is done programmatically by the AutoRubric engine in `eval_autorubric/`. Your job is to run it, interpret the result, and drive the improvement loop.

---

## Step 1 — Run the evaluator

```bash
venv/bin/python -m eval_autorubric.run_eval
```

This locates the latest `brief_v2_*`, `brief_v1_*`, and `brief_general_*` in `outputs/`, grades each atomically (one LLM call per criterion), applies the trend-continuity cap for stateless briefs, writes `outputs/eval_autorubric_<date>.md`, and appends a record to `state.json → autorubric_eval_history` (separate from the legacy `eval_history`).

**Optional — ensemble + reliability** (recommended when presenting): set two cross-family judges so the report includes inter-judge agreement (the reliability signal). Any LiteLLM model ids work; both must be reachable via `OPENROUTER_API_KEY`:

```bash
AUTORUBRIC_JUDGES="openrouter/anthropic/claude-haiku-4-5,openrouter/google/gemini-2.5-flash" \
  venv/bin/python -m eval_autorubric.run_eval
```

Read the printed `SUMMARY_JSON=...` line for the final scores and deltas.

---

## Step 2 — Read and interpret the report

Read `outputs/eval_autorubric_<date>.md` in full. In your reply to the user, summarize:
- The three final scores and the v2-vs-v1-vs-general deltas.
- Any **negative penalty** that fired on v2 (these are anti-patterns, not just low scores).
- If run as an ensemble: the mean inter-judge agreement, and name any criterion with agreement < 0.5 — those are low-reliability judgments to treat with caution / flag for human review.

---

## Step 3 — Improvement loop (patch CLAUDE.md)

This is AutoRubric's §5 "agent skill improvement" applied to our agent. For every **v2** dimension scoring **≤ 3**, and every **penalty that fired on v2**, append a dated patch to the `## Agent Improvement Notes` section of `CLAUDE.md`. Use the per-criterion reason from the report (the "v2 Improvement Targets" section) as the concrete, observed failure to fix.

Read `CLAUDE.md` first, then append (never overwrite existing notes):

```
### {YYYY-MM-DD} — {Dimension or penalty name} (AutoRubric: {score}/5 or "penalty fired")
- [Specific instruction tied to the exact failure the judge cited]
```

If nothing on v2 scored ≤ 3 and no penalty fired, state that no patch was needed.

---

## Step 4 — Report back

Give the user a short comparison-friendly summary: the AutoRubric scores, whether they agree with the most recent legacy `/eval-brief` scores (check `state.json → eval_history` vs `autorubric_eval_history`), and what (if anything) you patched. Do **not** edit any file under `eval/` — that is the legacy framework and must stay frozen for comparison.
