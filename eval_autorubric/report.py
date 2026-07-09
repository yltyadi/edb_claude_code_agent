"""
Render a grade_all() result into a markdown 3-way comparison report.

Three sections:
  1. Binary structural criteria  — PASS/FAIL per requirement
  2. Ordinal quality dimensions  — 1–5 per dimension
  3. Negative penalty criteria   — MET/ok per anti-pattern

Parallel structure to the legacy eval report so the two can be compared directly.
"""

from __future__ import annotations

from eval.rubric import LLM_DIMENSIONS
from eval_autorubric.rubric_def import BINARY_CRITERIA, PENALTIES

_ORDER = ["v2", "v1", "general"]
_LABEL = {"v2": "v2 Agent", "v1": "v1 Agent", "general": "General LLM"}


def _bin_row(c, results):
    cells = []
    for t in _ORDER:
        r = results.get(t)
        if not r:
            cells.append("—")
        else:
            met = r["binary"].get(c["id"])
            cells.append("✅" if met else "❌")
    return f"| {c['id']:<32} | {c['weight']:+.2f} | " + " | ".join(cells) + " |"


def _dim_row(dim, results):
    cells = []
    for t in _ORDER:
        r = results.get(t)
        if not r:
            cells.append("—")
        else:
            lvl = r["dims"].get(dim["id"])
            cells.append(f"{lvl}/5" if lvl is not None else "N/A")
    return f"| {dim['name']:<36} | {int(dim['weight']*100)}% | " + " | ".join(cells) + " |"


def _pen_row(pen, results):
    cells = []
    for t in _ORDER:
        r = results.get(t)
        if not r:
            cells.append("—")
        else:
            met = r["penalties"].get(pen["id"])
            cells.append("⚠️ MET" if met else "ok")
    return f"| {pen['id']:<32} | {pen['weight']:+.2f} | " + " | ".join(cells) + " |"


def _score_row(label, results, fmt):
    cells = [fmt(results[t]) if t in results else "—" for t in _ORDER]
    return f"| {label:<30} | " + " | ".join(cells) + " |"


def format_report(graded: dict, date_str: str, brief_names: dict[str, str]) -> str:
    results  = graded["results"]
    deltas   = graded["deltas"]
    judges   = graded["judges"]
    ensemble = graded["ensemble"]

    present      = [t for t in _ORDER if t in results]
    header_cols  = " | ".join(_LABEL[t] for t in _ORDER)
    sep          = "|".join([":--:"] * 3)

    bin_rows = "\n".join(_bin_row(c, results) for c in BINARY_CRITERIA)
    dim_rows = "\n".join(_dim_row(d, results) for d in LLM_DIMENSIONS)
    pen_rows = "\n".join(_pen_row(p, results) for p in PENALTIES)

    final_row = _score_row(
        "**Final Score / 100**", results,
        lambda r: f"**{r['final_score']:.1f}**")
    llm_row   = _score_row(
        "AutoRubric result.score", results,
        lambda r: f"{r['llm_score']:.3f}")

    # reliability
    if ensemble:
        rel_lines = [
            f"- **{_LABEL[t]}**: mean inter-judge agreement "
            f"{results[t]['mean_agreement']:.2f}"
            for t in present
            if results[t].get("mean_agreement") is not None
        ]
        rel = (
            f"Ensemble of {len(judges)} judges "
            f"({', '.join(j.split('/')[-1] for j in judges)}), majority vote.\n\n"
            + "\n".join(rel_lines)
        )
    else:
        rel = (
            f"Single judge (`{judges[0].split('/')[-1]}`). "
            "Set `AUTORUBRIC_JUDGES` to 2+ cross-family models for reliability signal."
        )

    # deltas
    delta_lines = []
    if "v2_vs_v1"  in deltas: delta_lines.append(f"- **v2 vs v1**: {deltas['v2_vs_v1']:+.1f} pts")
    if "v2_vs_gen" in deltas: delta_lines.append(f"- **v2 vs General**: {deltas['v2_vs_gen']:+.1f} pts")
    if "v1_vs_gen" in deltas: delta_lines.append(f"- **v1 vs General**: {deltas['v1_vs_gen']:+.1f} pts")

    # improvement targets for v2
    targets = []
    if "v2" in results:
        r = results["v2"]
        for c in BINARY_CRITERIA:
            if not r["binary"].get(c["id"]):
                targets.append(f"- **{c['id']}** (FAIL): {r['reasons'].get(c['id'], '')[:200]}")
        for d in LLM_DIMENSIONS:
            s = r["dims"].get(d["id"])
            if s is not None and s <= 3:
                targets.append(f"- **{d['name']}** ({s}/5): {r['reasons'].get(d['id'], '')[:200]}")
        for p in PENALTIES:
            if r["penalties"].get(p["id"]):
                targets.append(f"- **penalty: {p['id']}**: {r['reasons'].get(p['id'], '')[:200]}")
    targets_block = (
        "\n".join(targets)
        if targets
        else "*None — v2 passed all binary checks, scored > 3 on every dimension, and tripped no penalties.*"
    )

    tokens = " / ".join(
        f"{_LABEL[t]}: {results[t]['total_tokens'] or '?'}" for t in present)

    return f"""# EDB Agent Evaluation Report — AutoRubric Framework
**Date:** {date_str}
**Framework:** AutoRubric (analytic rubric, atomic per-criterion judging)
**v2 brief:** {brief_names.get('v2', '(none)')}
**v1 brief:** {brief_names.get('v1', '(none)')}
**General brief:** {brief_names.get('general', '(none)')}
**Judges:** {', '.join(judges)}

---

## 1 — Binary Structural Requirements (✅ = MET, ❌ = FAIL)

| Requirement | Wt | {header_cols} |
|-------------|:--:|{sep}|
{bin_rows}

## 2 — Ordinal Quality Dimensions (1–5, atomic per-criterion judging)

| Dimension | Wt | {header_cols} |
|-----------|:--:|{sep}|
{dim_rows}

## 3 — Negative Penalties (anti-patterns — MET is bad)

| Penalty | Wt | {header_cols} |
|---------|:--:|{sep}|
{pen_rows}

## Reliability

{rel}

---

## Final Scores

| | {header_cols} |
|--|{sep}|
{llm_row}
{final_row}

{chr(10).join(delta_lines)}

**Token usage:** {tokens}

---

## v2 Improvement Targets

{targets_block}
"""
