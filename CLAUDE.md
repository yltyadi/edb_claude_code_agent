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
