# EDB Macro Intelligence Agent — Project Context

## What this project is

This is the Emirates Development Bank (EDB) macro intelligence workspace. EDB is
the UAE's primary development finance institution, wholly government-owned. Its mandate
is economic diversification under **Operation 300bn**: grow the industrial sector's GDP
contribution from AED 133bn to AED 300bn by 2031. EDB is NOT a commercial bank —
decisions are governed by developmental impact, not profit.

## The five priority sectors (primary mandate filter)

Every macro signal must be evaluated for impact on one or more of:

| # | Sector | Key themes |
|---|--------|-----------|
| 1 | **Advanced Technology** | AI, semiconductors, software, digital infrastructure |
| 2 | **Manufacturing** | Industrial capex, supply chains, input costs, UAE exports |
| 3 | **Healthcare** | Medical devices, pharma, hospital infrastructure |
| 4 | **Renewables** | Solar, wind, green hydrogen, energy transition financing |
| 5 | **Food Security** | Agri-tech, global commodity prices, food supply chains |

Ignore signals that do not affect these sectors or EDB's funding cost structure.
Never produce generic market commentary.
Every sector matrix row must have a direction and urgency justified by data —
never write "no direct signal" as a complete row entry.

## AED/USD peg transmission chain

The UAE dirham is pegged to USD at 3.6725. Every rate signal must be traced through
all four steps:

```
Fed rate change
  → CBUAE mirrors within 24-48h (Base Rate ≈ Fed Funds + 10-30 bps)
  → EIBOR 3M shifts proportionally
  → EDB floating-rate portfolio reprices
  → SME debt serviceability changes
```

## Reference loan for EIBOR sensitivity

- Principal: AED 5,000,000
- Tenor: 7 years, quarterly amortisation
- Rate: EIBOR 3M + 200 bps spread
- Use this for all DSCR / payment impact calculations
- Always compute: base ADS, +25bps, −25bps, −50bps scenarios

## State & session memory

At the **start** of every `/edb-brief` run, read `outputs/state.json` and extract:
- `baselines.*` — yesterday's key figures for trend comparisons
- `streaks.*` — consecutive session counts
- `last_run.date` — to compute days-since

Use these to add temporal depth to the brief: "EIBOR unchanged for 187 days",
"Brent's 4th consecutive declining session", "Fed has held for 4 consecutive meetings".
At least one Type A paragraph and one sector matrix row should include trend language.

At the **end** of every `/edb-brief` run, update `outputs/state.json` with:
- Today's key figures in `baselines`
- Updated streaks (increment if direction unchanged, reset if reversed)
- `signals_fired_last_run` list
- `last_run` metadata

## Output file naming & versioning

All output files go to `outputs/`. Naming convention:

| File type | Pattern |
|-----------|---------|
| EDB specialised brief | `outputs/brief_v{N}_YYYY-MM-DD_HHMM.md` |
| General baseline brief | `outputs/brief_general_YYYY-MM-DD.md` |
| Eval comparison report | `outputs/eval_YYYY-MM-DD.md` |
| Cross-session state | `outputs/state.json` |

Current agent version: **v2** (state.json + CLAUDE.md feedback loop).
Read the version from `state.json → agent_version` and use it in the filename.
Include `**Agent version:** v{N}` in the brief header metadata block.

## How to run the data tools

All specialized data tools are callable via Bash:

```bash
python3 run_tools.py fred FEDFUNDS              # Fed Funds Rate
python3 run_tools.py fred DGS10                 # 10-yr Treasury
python3 run_tools.py fred DCOILBRENTEU          # Brent crude
python3 run_tools.py fred DCOILWTICO            # WTI crude
python3 run_tools.py fred INDPRO                # US Industrial Production
python3 run_tools.py fred CPIAUCSL              # US CPI
python3 run_tools.py fred T10YIE                # 10-yr breakeven inflation
python3 run_tools.py worldbank AE NY.GDP.MKTP.CD   # UAE GDP
python3 run_tools.py worldbank AE NV.IND.TOTL.ZS   # UAE industry % GDP
python3 run_tools.py worldbank AE FP.CPI.TOTL.ZG   # UAE inflation
python3 run_tools.py worldbank AE BX.KLT.DINV.CD.WD # UAE FDI inflows
python3 run_tools.py cbuae                      # CBUAE Base Rate + policy statement
python3 run_tools.py opec                       # OPEC basket price + UAE quota
```

All commands print JSON to stdout. Run them from the project root.
FRED_API_KEY must be set in .env (free key at fred.stlouisfed.org).

## Invoke the brief

Type `/edb-brief` to run the full pipeline.

---

## Agent Improvement Notes

*This section is appended automatically by `/eval-brief` when any dimension scores ≤ 3.
Do not delete entries — they accumulate as a learning history.*

### 2026-06-22 — Quantitative Accuracy (scored 3/5)
- **Always run all four required calculations in every brief, including same-day refreshes.** The 0800 brief omitted the petrochemical feedstock pass-through and the Operation 300bn annual run-rate because it was framed as a "same-day refresh focused on new signals." Being a refresh does not waive the calculation requirement — include all four in Step 3 regardless of run frequency.
- **Petrochemical pass-through template:** Use Brent delta × 60% pass-through rate, applied to UAE petrochemical sector cost base (~AED 17.5bn feedstock). Report as a percentage and an AED figure. Even when the delta is small, the calculation must appear.
- **Operation 300bn run-rate template:** Always compute current AED figure vs AED 300bn target by 2031, reporting (a) % of gap closed from AED 133bn baseline (not % of total target — 200/300=66.7% is the wrong method; correct is (200−133)/(300−133)=40.1%), (b) AED remaining, (c) AED/yr pace required. This calculation takes one line and must appear in every brief.

### 2026-07-01 — Data Grounding (scored 3/5)
- **The EIBOR estimation basis must appear as the first line of the calculation code block**, not only in the narrative prose. Use exactly: `EIBOR source: estimated (state.json baseline; CBUAE base rate X.XX% confirmed [date]; assumed unchanged; [N] consecutive days)`. The rubric judges whether a reader of the calculation block alone can trace the number — if the source is only in the surrounding text, it scores 3 not 5.
- **The Sources section is mandatory and must list all data series with their vintage dates.** Flag stale FRED series (those with a value date more than 7 days before the brief date) by name. Format: `DCOILBRENTEU: stale (last value June 22) — overridden by web $72.91`. Truncating the brief before the Sources section produces a fail regardless of body quality.
- **Keep body concise enough that Sources and Methodology always fit within the token budget.** Target ≤ 3,500 words for the full brief body (Type A + B + C). If a section is running long, trim the sector matrix narrative rather than omitting Sources/Methodology — those trailing sections are harder to recover.

### 2026-07-01 — Structure Completeness (scored 3/5)
- **Use exactly `**Key number:**` (bold, with colon, lowercase 'n')** — not `### Key Number`, not `**Key Number:**` (capital N). The automated check uses the regex `(?i)\*\*key\s+number` which requires `**key` as the opener; a `###` heading prefix causes the check to fail.
- **Use exactly `**Watch list — next 72 hours:**`** — not `### 72-Hour Watchlist`, not `### Watch List`. The check looks for `watch\s+list` preceded by `**`.
- **Sources and Methodology are mandatory final sections.** Never terminate the brief before writing both. If the generation is approaching the token limit, compress the Type C Stakeholder Bulletin (it is the lowest-priority section) before compressing Sources/Methodology.
- **Do not generate YAML frontmatter.** The header block must begin with `---` (a plain markdown horizontal rule on its own line), then `# EDB Daily Macro Intelligence Brief` as a heading, then bold key-value pairs (`**Date:**`, `**Agent version:**`, `**Generated:**`, `**Signals processed:**`, `**Signals passing mandate filter:**`), then another `---`. YAML between `---` markers is parsed as frontmatter by renderers and breaks all header regex checks.

### 2026-07-01 — Data Integrity (scored 3/5)
- **EIBOR estimation chain belongs in the calculation block, not only in Methodology.** The first line of every calculation code block must state the EIBOR source: `EIBOR source: estimated (state.json baseline X.XX%; CBUAE base rate X.XX% confirmed [date]; last live EIBOR confirmation [date]; N consecutive unchanged days)`. The rubric checks whether the calculation block is self-contained — a reader who skips Methodology must still see the estimation basis.
- **Stale FRED series must be disclosed by name with vintage dates in both the body and the Methodology section.** Format: "DCOILBRENTEU: stale (FRED last value June 22 2026) — overridden by web-sourced $72.91." Never use a FRED stale value silently; always state the override.
- **The Methodology section must be present in every brief.** It is the single consolidation point for all gap disclosures: which series are stale, how EIBOR was estimated, which web sources overrode tool data, and what data was unavailable (e.g. OPEC basket null). A brief without a Methodology section cannot score above 3/5 on Data Integrity regardless of body quality.

### 2026-07-13 — peg_chain_traced (AutoRubric: binary FAIL)
- **The AED/USD peg transmission chain must appear as one explicit, connected arrow-chain sentence in every brief, including same-day refreshes** — not as facts scattered across separate paragraphs (Fed hold mentioned in one place, CBUAE rate in another, EIBOR in a third). The judge's exact objection: "it does NOT explicitly trace the transmission chain starting from a Federal Reserve decision... no explicit causal chain from a specific Fed decision to these subsequent moves is presented. The criterion requires the chain to be 'explicitly traced,' not merely referenced in separate sections." Use the literal form: `Fed [action/hold] at X.XX–X.XX% → CBUAE mirrors at X.XX% (within 24–48h) → EIBOR 3M at X.XX% → EDB floating-rate portfolio priced at EIBOR + 200bps = X.XX% → SME quarterly debt service [impact]`. This chain sentence was present in an earlier same-day brief (0820) and was dropped from the following same-day refresh (0843) because the refresh only carried forward the surrounding narrative, not this specific line — treat this chain sentence as a required, non-droppable element of Type A on every run, not something that can be assumed "already covered" by an earlier brief today.

### 2026-07-13 — silent_stale_or_estimated_data (AutoRubric: penalty fired) <!-- auto:penalty:silent_stale_or_estimated_data -->
- **Disclosing the EIBOR estimation basis once, before the calculation block, is not sufficient — the penalty checks for disclosure "at the point of use."** The judge's exact objection: "the submission fails this test by presenting the estimated rate in active calculations (loan ADS, all-in rates) without a contemporaneous flag like '(est.)' or 'estimated' adjacent to the figure itself." In addition to the required `EIBOR source: estimated (...)` header line at the top of the calculation block, tag every subsequent inline use of the EIBOR figure with `(est.)` directly next to the number, e.g. `EIBOR 3.90% (est.) → all-in 5.90% (est.)`, in every scenario line (base, +25bps, −25bps, −50bps) — not just once at the top.

### 2026-07-13 — Output Structure Completeness (AutoRubric: 3/5, likely scoring artifact — flagged for human review, not a content patch)
- The judge's full written reason for this run was entirely positive with no stated deficiency ("exemplifies all three required types with complete substantive detail... every sub-field is populated with specific, sourced, quantified analysis"), yet it selected the "Adequate" (3/5) option rather than "Strong" or "Exemplary" on the 5-point scale. This is the second consecutive run where this dimension capped at 3/5 despite a clean structural checklist (all binary structure criteria passed) and a glowing text justification — worth flagging as a possible judge/rubric calibration issue (option-label vs. free-text mismatch) rather than a fixable brief defect. Do not blindly rewrite Type A/B/C structure in response to this score without independently confirming a concrete gap; cross-check against the binary `sections_complete` result (which has passed both times) before treating this as ground truth.

### 2026-07-14 — unsupported_number (AutoRubric: penalty fired) <!-- auto:penalty:unsupported_number -->
- **Every material figure — a rate, price, AED amount, or percentage that drives a conclusion — must trace to a shown calculation block or a named source.** The 2026-07-14 brief tripped this penalty by quoting three *different* oil-fiscal numbers that read as the same quantity: `AED +89.3bn/yr` (headline, "uplift vs pre-escalation"), `AED 163.5bn/yr` (Key number, "surplus vs $55/bbl breakeven"), and `AED +41.5bn/yr` ("single-session gain"). These are three legitimately different quantities, but they were not labelled as such and `+89.3bn` was never shown in a calculation.
- **Rule 1 — compute each derived quantity ONCE, in a calculation block, then reuse that exact number everywhere** (headline, Key number, sector matrix, Type B). Never let the headline, Key number, and matrix quote different AED figures for what a reader will take to be the same thing.
- **Rule 2 — when you report more than one oil-fiscal figure, label precisely what each represents** on the same line: "uplift vs pre-crisis baseline", "total surplus above the ~$55/bbl breakeven", "single-session change". Different framings → different numbers → each needs its own labelled calc line.
- **Rule 3 — the Key number and the headline must be internally consistent.** If the headline cites an uplift and the Key number cites a surplus, state both bases explicitly so the reader can reconcile them; do not present one as if it contradicts the other.
