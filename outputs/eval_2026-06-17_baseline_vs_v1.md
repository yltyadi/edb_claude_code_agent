# EDB Agent Evaluation Report
**Date:** 17 June 2026
**EDB brief:** `outputs/edb_brief_2026-06-17_0700.md`
**General brief:** `eval/results/general_2026-06-17.md`
**Judge:** Claude Code (claude-sonnet-4-6), no API calls

---

## Automated Checks (40% of score)

| Check | EDB Agent | General Agent |
|-------|:---------:|:-------------:|
| Executive Brief (Type A) section present | ✓ | ✗ |
| Credit Alert (Type B) section present | ✓ | ✗ |
| Stakeholder Bulletin (Type C) section present | ✓ | ✗ |
| Sector impact matrix table (5 rows) present | ✓ | ✗ |
| Key number field present | ✓ | ✗ |
| Watch list (next 72 h) present | ✓ | ✗ |
| Action flag (MONITOR/REVIEW/ESCALATE) present | ✓ | ✓ * |
| Python calculation output block present | ✓ | ✗ |
| Sources section present | ✓ | ✓ |
| Methodology / data-gap note present | ✓ | ✗ |
| EIBOR explicitly mentioned | ✓ | ✗ |
| AED/USD peg transmission chain traced (Fed→CBUAE→EIBOR) | ✓ | ✗ |
| Date header present | ✓ | ✓ |
| All five EDB priority sectors mentioned | ✓ | ✗ |
| **TOTAL** | **14 / 14** | **3 / 14** |

\* False positive — the word "Review" appears in a section heading, not as a formal action flag.

---

## LLM Dimensions (60% of score)

| Dimension | Wt | EDB Agent | General Agent |
|-----------|:--:|:---------:|:-------------:|
| Mandate Relevance | 22% | 5 / 5 | 3 / 5 |
| Data Grounding & Source Citation | 18% | 5 / 5 | 4 / 5 |
| Quantitative Accuracy | 18% | 5 / 5 | 1 / 5 |
| Output Structure Completeness | 14% | 5 / 5 | 1 / 5 |
| Action Specificity | 14% | 5 / 5 | 2 / 5 |
| Data Integrity & Gap Disclosure | 14% | 5 / 5 | 3 / 5 |

### Reasoning

**Mandate Relevance**
- *EDB Agent (5/5):* Every paragraph anchors to a named EDB sector or the EIBOR/peg chain. The headline ties the oil crash directly to Operation 300bn fiscal headroom. The sector matrix maps all five sectors by name. Zero generic market commentary.
- *General Agent (3/5):* Section 5 is sector-aware but addresses "UAE businesses" generically rather than by the five EDB sectors. Sections 1–3 are solid macro but read as general newsletter content. The capital-markets IPO paragraph is off-mandate entirely.

**Data Grounding & Source Citation**
- *EDB Agent (5/5):* Every number traces to a named source. FRED failure, OPEC null, World Bank vintage, EIBOR estimation, and CBUAE rate date are all explicitly disclosed with fallback sources or verification paths. No hallucinated data.
- *General Agent (4/5):* Ten hyperlinked sources covering all major claims. Penalised for a factual inconsistency ("unanimous, though Miran dissented" — cannot be both) and no disclosure of data vintage or estimation assumptions.

**Quantitative Accuracy & Calculation Discipline**
- *EDB Agent (5/5):* Full EIBOR sensitivity run (AED 874,167 base ADS; ±25bps, −50bps scenarios); oil revenue impact (AED 105.8bn/yr on 3.2m bbl/day × $24.66 × 365 × 3.6725 peg); petrochemical pass-through (−14.5%); Operation 300bn run-rate (AED 20bn/yr); all internally consistent.
- *General Agent (1/5):* Zero calculations performed. All numbers quoted from source articles with no derivation, no scenarios, no EIBOR math, no fiscal impact quantification.

**Output Structure Completeness**
- *EDB Agent (5/5):* Type A complete (headline, sector matrix, key number, 72h watchlist); Type B ×3 signals each with exposure, quantified impact block, and action flag; Type C (what happened, what it means, what to consider). Every required sub-field present and substantive.
- *General Agent (1/5):* Five numbered sections covering the macro topics competently, but no Type A, B, or C sections; no sector matrix; no key number; no per-signal watchlist or action flags.

**Action Specificity**
- *EDB Agent (5/5):* MONITOR on EIBOR with a concrete escalation trigger ("if June/July CPI exceeds 4.5%"); ESCALATE on oil with named teams (Manufacturing, Renewables sector teams) and a duration threshold ("if oil stays below $80 for more than one quarter"); MONITOR on IMF with specific reassessment milestone (Q3 close, October 2026 Article IV). Watchlist names Warsh's press conference time, Iran MOU volume guidance, and OPEC+ emergency session.
- *General Agent (2/5):* No formal MONITOR/REVIEW/ESCALATE flags per signal. Section 5 offers directional advice ("lock in forward contracts", "manage interest-rate exposure") but without portfolio-specific thresholds, team routing, or time horizons.

**Data Integrity & Gap Disclosure**
- *EDB Agent (5/5):* Eight discrete gaps named: FRED API failure (all 7 series listed), EIBOR estimated (verification URL provided), OPEC tool null (reason stated), World Bank 2024 vintage (explicitly flagged), CBUAE rate date (07 Apr 2025 noted), Warsh press conference timing, oil production figure labelled estimate, fiscal breakeven labelled estimate.
- *General Agent (3/5):* Sources hyperlinked but no methodology section, no disclosure of data vintage, and no flagging of the EIBOR estimation or World Bank lag. Fed vote inconsistency unexplained.

---

## Final Scores

|  | EDB Agent | General Agent |
|--|:---------:|:-------------:|
| Automated checks (40% weight) | 40.0 / 40 | 8.6 / 40 |
| LLM dimensions (60% weight) | 60.0 / 60 | 28.8 / 60 |
| **Final Score** | **100.0 / 100** | **37.4 / 100** |
| **Delta** | **+62.6 pts** | |

---

## Key Differentiators

1. **Quantitative computation is the single biggest gap (−18 weighted points).** The EDB agent ran Python calculations producing computed outputs (AED 874,167 ADS, AED 105.8bn oil revenue impact, −14.5% petrochemical pass-through, AED 20bn/yr run-rate). The general agent stated every number from an article without deriving anything. For a development bank making credit decisions, uncomputed numbers are not actionable.

2. **Structured output format enables downstream consumption (−11.2 weighted points).** The EDB agent's Type A/B/C format with sector matrix, key number, and per-signal action flags means any reader — credit officer, sector team, board — can immediately navigate to the relevant section. The general agent's prose is readable but requires interpretation at each consumption point.

3. **Portfolio-specific action flags with concrete triggers vs. generic advice (−8.4 weighted points).** "ESCALATE to Manufacturing and Renewables sector teams if Brent stays below $80 for one quarter" is immediately actionable. "Businesses should consider managing interest-rate exposure" is not. The EDB agent's action flags name teams, thresholds, and timelines.

4. **Data gap transparency differentiates a safe brief from a misleading one (−2.8 weighted points).** The EDB agent's methodology section lists 8 gaps and estimates with verification paths. The general agent's omission of this section means a reader cannot assess the reliability of any number — a significant risk for investment decisions.

5. **Mandate filtering cuts noise.** The general agent's brief contains an IPO pipeline section (aviation, utilities) that is irrelevant to EDB's industrial development mandate. The EDB agent's signal filter (sector_relevance ≥ 3) prevents off-mandate content from consuming reader attention.

---

*Evaluation methodology: automated checks via `python3 eval/check.py` (14 binary regex checks); LLM dimension scoring by Claude Code (claude-sonnet-4-6) reading both briefs against criteria in `eval/rubric.py`. No external API calls.*
