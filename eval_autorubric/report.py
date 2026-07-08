"""
Render a grade_all() result into a markdown 3-way comparison report.

Deliberately parallel in shape to the OLD eval report (outputs/eval_*.md) so the
two frameworks can be laid side by side, but adds the AutoRubric-native columns:
negative penalties and inter-judge reliability.
"""

from __future__ import annotations

from eval.rubric import LLM_DIMENSIONS
from eval_autorubric.rubric_def import PENALTIES

_ORDER = ["v2", "v1", "general"]
_LABEL = {"v2": "v2 Agent", "v1": "v1 Agent", "general": "General"}


def _cell(v):
    return "—" if v is None else v


def _dim_row(dim, results):
    cells = []
    for t in _ORDER:
        r = results.get(t)
        if not r:
            cells.append("—")
        else:
            lvl = r["dims"].get(dim["id"])
            cells.append(f"{lvl}/5" if lvl is not None else "N/A")
    return f"| {dim['name']:<28} | {int(dim['weight']*100)}% | " + " | ".join(cells) + " |"


def _pen_row(pen, results):
    cells = []
    for t in _ORDER:
        r = results.get(t)
        if not r:
            cells.append("—")
        else:
            met = r["penalties"].get(pen["id"])
            cells.append("⚠️ MET" if met else "ok")
    return f"| {pen['id']:<32} | {pen['weight']:+.0f} | " + " | ".join(cells) + " |"


def _final_row(label, key, results, fmt):
    cells = []
    for t in _ORDER:
        r = results.get(t)
        cells.append(fmt(r) if r else "—")
    return f"| {label:<26} | " + " | ".join(cells) + " |"


def format_report(graded: dict, date_str: str, brief_names: dict[str, str]) -> str:
    results = graded["results"]
    deltas = graded["deltas"]
    judges = graded["judges"]
    ensemble = graded["ensemble"]

    present = [t for t in _ORDER if t in results]
    header_cols = " | ".join(_LABEL[t] for t in _ORDER)
    sep = "|".join([":--:"] * 3)

    dim_rows = "\n".join(_dim_row(d, results) for d in LLM_DIMENSIONS)
    pen_rows = "\n".join(_pen_row(p, results) for p in PENALTIES)

    struct_row = _final_row(
        "Structural (of 20)", "structural", results,
        lambda r: f"{r['structural_passed']}/{r['structural_total']}")
    llm_row = _final_row(
        "LLM score (norm 0–1)", "llm_norm", results,
        lambda r: f"{r['llm_norm']:.3f}")
    final_row = _final_row(
        "**Final Score / 100**", "final_score", results,
        lambda r: f"**{r['final_score']:.1f}**")

    # reliability block
    if ensemble:
        rel_lines = [
            f"- **{_LABEL[t]}**: mean inter-judge agreement "
            f"{results[t]['mean_agreement']:.2f}" for t in present
            if results[t].get("mean_agreement") is not None
        ]
        rel = ("Ensemble of "
               f"{len(judges)} judges ({', '.join(j.split('/')[-1] for j in judges)}), "
               "majority vote. Mean inter-judge agreement per brief (reliability "
               "indicator — low values flag criteria to route to human review):\n\n"
               + "\n".join(rel_lines))
    else:
        rel = (f"Single judge (`{judges[0].split('/')[-1]}`). No inter-judge "
               "reliability signal — set `AUTORUBRIC_JUDGES` to 2+ models "
               "(ideally cross-family) to enable Cohen's κ / agreement.")

    # deltas
    delta_lines = []
    if "v2_vs_v1" in deltas:
        delta_lines.append(f"- **v2 vs v1**: {deltas['v2_vs_v1']:+.1f} pts")
    if "v2_vs_gen" in deltas:
        delta_lines.append(f"- **v2 vs General**: {deltas['v2_vs_gen']:+.1f} pts")
    if "v1_vs_gen" in deltas:
        delta_lines.append(f"- **v1 vs General**: {deltas['v1_vs_gen']:+.1f} pts")

    # improvement targets for v2 (dims <=3 or any penalty MET)
    targets = []
    if "v2" in results:
        r = results["v2"]
        for d in LLM_DIMENSIONS:
            s = r["dims"].get(d["id"])
            if s is not None and s <= 3:
                targets.append(f"- **{d['name']}** ({s}/5): {r['reasons'].get(d['id'], '')[:200]}")
        for p in PENALTIES:
            if r["penalties"].get(p["id"]):
                targets.append(f"- **penalty fired: {p['id']}**: {r['reasons'].get(p['id'], '')[:200]}")
    targets_block = "\n".join(targets) if targets else "*None — v2 scored > 3 on every dimension and tripped no penalties.*"

    tokens = " / ".join(
        f"{_LABEL[t]}: {results[t]['total_tokens'] or '?'}" for t in present)

    return f"""# EDB Agent Evaluation Report — AutoRubric Framework
**Date:** {date_str}
**Framework:** AutoRubric (analytic rubric, atomic per-criterion judging)
**v2 brief:** {brief_names.get('v2', '(none)')}
**v1 brief:** {brief_names.get('v1', '(none)')}
**General brief:** {brief_names.get('general', '(none)')}
**Judges:** {', '.join(judges)}
**Aggregation:** structural 40% (deterministic) + LLM 60% (AutoRubric normalized)

---

## LLM Quality Dimensions — atomic per-criterion (1–5)

| Dimension | Wt | {header_cols} |
|-----------|:--:|{sep}|
{dim_rows}

## Negative Penalties (anti-patterns — MET is bad)

| Penalty | Wt | {header_cols} |
|---------|:--:|{sep}|
{pen_rows}

## Reliability

{rel}

---

## Final Scores

| | {header_cols} |
|--|{sep}|
{struct_row}
{llm_row}
{final_row}

{chr(10).join(delta_lines)}

**Token usage:** {tokens}

---

## v2 Improvement Targets (dimensions ≤ 3 or penalties fired)

{targets_block}
"""
