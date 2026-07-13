---
# EDB Daily Macro Intelligence Brief
**Date:** 2026-07-13
**Agent version:** v2
**Generated:** 2026-07-13T06:41 UTC
**Signals processed:** 20
**Signals passing mandate filter:** 13

---

## Executive Brief (Type A)

**Headline:** No new macro event since the 06:18 UTC brief 23 minutes ago — this is a same-day refresh — but the Strait of Hormuz standoff has escalated in character: US Central Command has now publicly denied Iran's "closed until further notice" declaration and confirmed it has conducted additional strikes to keep the strait open, turning a unilateral closure claim into an active, contested military stand-off. `[CONTINUING — escalated, Day 1 of closure / Day 5 of exchange]`

Brent is intraday-flat at $79.0–79.2 (vs the $79.11 baseline set this morning), meaning markets have not yet re-rated the CENTCOM pushback — a de-escalation signal worth watching, not yet worth trading on. The CBUAE base rate has now held for **214 consecutive days** at 3.65%, and EIBOR 3M remains estimated flat at 3.900% for a 3rd consecutive day. Tomorrow's June CPI print (July 14, 08:30 ET) remains the single most consequential near-term data release ahead of the July 29 FOMC. EDB's priority is unchanged from this morning: continue sector triage on Hormuz exposure while treating the CENTCOM denial as a reason to hold rather than escalate the internal risk posture.

### Sector Impact Matrix

| Sector | Signal | Direction | Urgency |
|---|---|---|---|
| **Advanced Technology** | `[CONTINUING]` Hormuz standoff still threatens sea-freight logistics for semiconductor/hardware imports; UAE's OPEC-exit fiscal surplus ($300.8mn/day crude revenue at $79.15 Brent) creates offsetting fiscal space for tech investment | ↑ fiscal offset / ↓ logistics risk | **HIGH** |
| **Manufacturing** | `[CONTINUING]` AED 180bn Make it in the Emirates procurement pipeline unchanged; petrochemical feedstock cost now AED 1,448mn/yr additional (AED 121mn/month) at current Brent, essentially flat vs this morning's AED 1,440mn estimate | ↑ demand pipeline / ↓ input costs | **CRITICAL** |
| **Healthcare** | `[CONTINUING]` UAE imports ~85% of medical supplies via sea; Hormuz standoff still the binding risk; CENTCOM's active strikes to preserve freedom of navigation is a mitigating factor not yet reflected in supply-chain planning | ↓ supply-chain risk | **CRITICAL** |
| **Renewables** | `[CONTINUING]` Fiscal buffer of $24.15/bbl above the ~$55/bbl UAE breakeven still funds solar/green-hydrogen co-financing capacity; Hormuz standoff reinforces the domestic-energy-independence case | ↑ fiscal capacity | **HIGH** |
| **Food Security** | `[CONTINUING]` UAE imports ~90% of food via sea; Fujairah bypass (1.5 mb/d) still covers ~50% of at-risk export/import corridor volume; no new commodity-price signal since this morning | ↓ supply-chain risk | **CRITICAL** |

**Key number:** AED 100bn — the remaining gap to the AED 300bn Operation 300bn target; at the current AED 6.7bn/yr pace the target is reached ~2040.9 (9.9 years late), but a 20% conversion of the AED 180bn Make it in the Emirates pipeline lifts the pace to AED 13.9bn/yr, cutting the target date to ~2033.2 (2.2 years late).

**Watch list — next 72 hours:**
- **July 14, 08:30 ET — US June CPI (BLS):** a print above 4.3% YoY raises July 29 hike probability above the current ~25%; a print at/below 4.0% reinforces the hold.
- **July 13–14 — CENTCOM vs. Iran Hormuz standoff:** watch for Lloyd's of London insurance-market suspension notices, Oman mediation statements, or a formal Iranian retraction/confirmation of the closure.
- **July 13–14 — ADNOC Fujairah pipeline throughput:** any confirmed capacity increase above 1.5 mb/d would materially reduce UAE revenue-at-risk from a full closure scenario.
- **July 29, 14:00 ET — FOMC rate decision:** no Summary of Economic Projections at this meeting; markets price ~25% odds of a 25bps hike given a committee split roughly down the middle per the July 10 minutes.

---

## Credit Team Alert (Type B)

**Signal:** Strait of Hormuz closure claim contested by US Central Command, which reports additional strikes to preserve freedom of navigation (Bloomberg, Yahoo Finance, Wikipedia — July 13, 2026, `[CONTINUING — escalated]`, Day 1 of closure claim / Day 5 of active exchange since the July 8 ceasefire collapse).
**Portfolio exposure:** EDB floating-rate SME loan book (EIBOR 3M + 200bps reference structure); import-dependent healthcare, food security, and technology-hardware borrowers; petrochemical-adjacent manufacturing borrowers exposed to feedstock cost pass-through.

**Quantified impact:**
```
EIBOR source: estimated (state.json baseline 3.900%; CBUAE base rate 3.65% confirmed
July 13 2026; last live EIBOR confirmation July 10 2026; 3 consecutive unchanged days)

Reference loan: AED 5,000,000 | 7yr (28 quarters) | EIBOR 3M + 200bps | quarterly amort.
Principal per quarter: AED 5,000,000 / 28 = AED 178,571

Base case (EIBOR 3.90% -> all-in 5.90%):
  Q interest = 5,000,000 x 5.90% / 4 = AED 73,750
  Q ADS = 178,571 + 73,750 = AED 252,321
  Annualised ADS = AED 1,009,286

+25bps (EIBOR 4.15% -> all-in 6.15%):
  Q ADS = AED 255,446 | Annualised = AED 1,021,786 | delta = +AED 12,500/yr
-25bps (EIBOR 3.65% -> all-in 5.65%):
  Q ADS = AED 249,196 | Annualised = AED 996,786 | delta = -AED 12,500/yr
-50bps (EIBOR 3.40% -> all-in 5.40%):
  Q ADS = AED 246,071 | Annualised = AED 984,286 | delta = -AED 25,000/yr

Oil fiscal impact (Brent latest check $79.15 vs FRED-stale July 6 $69.56):
  Delta: +$9.59/bbl (+13.8%)
  Daily UAE crude revenue at $79.15: 3.8mn bbl x $79.15 = $300.8m/day
  Daily gain vs July 6 baseline: +$36.4m/day -> annualised +$13.30bn/yr -> AED +48.85bn/yr (x3.6725)
  Fiscal breakeven buffer: $79.15 - $55.00 = $24.15/bbl
  vs. this morning's $79.11 baseline: +$0.04/bbl (intraday-flat, no material new fiscal signal)

Petrochemical feedstock pass-through (60% of Brent delta vs July 6 base):
  Effective increase: $9.59 x 60% = $5.75/bbl = 8.27% of July 6 base
  AED 17.5bn feedstock base x 8.27% = AED 1,448mn/yr additional (AED 121mn/month)

Operation 300bn run-rate:
  Gap closed: (200-133)/(300-133) = 40.1% | Remaining: AED 100bn
  Required pace: AED 20.0bn/yr | Current estimated pace: AED 6.7bn/yr | Shortfall: AED 13.3bn/yr
  At current pace: target reached ~2040.9 (9.9 yrs late)
  With 20% Make it in Emirates conversion: pace AED 13.9bn/yr -> ~2033.2 (2.2 yrs late)
```

**Action flag:** MONITOR — EDB Credit Committee should monitor (not yet escalate) the Hormuz standoff given Brent's intraday-flat reading against the CENTCOM denial; re-escalate to REVIEW if Brent moves outside the $76–83 range or if Lloyd's of London suspends war-risk cover for the strait, and re-escalate to ESCALATE if the June 14 CPI print exceeds 4.3% YoY (raising July 29 hike odds materially) concurrent with a sustained Hormuz disruption — the compounding scenario that stresses SME DSCR headroom on the AED 5mn reference loan class.

---

## Stakeholder Bulletin (Type C)

**What happened:** Iran's claimed closure of the Strait of Hormuz is now actively disputed — US Central Command says it has struck to keep the waterway open and denies the strait is closed. Oil prices, which jumped 4% on Sunday's initial announcement, have not moved further today, sitting near $79/barrel. Nothing new has emerged on the Federal Reserve or the UAE central bank since this morning's brief; both remain on hold.

**What it means for UAE businesses:** The standoff over Hormuz is the same live risk as this morning — roughly 20% of world oil and 20% of LNG trade transits the strait, and businesses relying on sea imports for medical supplies, food, or electronics components face the same disruption risk as before. The fact that oil prices have stopped rising, even as the US military pushes back on Iran's claim, is a tentative sign the market does not expect a prolonged full closure, but this could reverse quickly.

**What businesses should consider:** Continue reviewing 30-day inventory buffers for imported medical supplies, food staples, and electronics/components. Financing costs on UAE dirham loans remain unchanged for now — EIBOR has been flat for three straight days and the central bank has held its rate for 214 consecutive days — but tomorrow's US inflation report (June CPI, July 14) is the next event that could move borrowing costs, ahead of the Fed's July 29 decision.

---

## Sources

| Series | Source | Value | Date | Status |
|---|---|---|---|---|
| FEDFUNDS | FRED (monthly) | 3.63% | 2026-06-01 | **STALE** (42 days) — assumed unchanged at 3.50–3.75% target range per June 17 FOMC decision |
| DGS10 | FRED (daily) | 4.54% | 2026-07-09 | Valid (4 days old) |
| DCOILBRENTEU | FRED (daily) | $69.56 | 2026-07-06 | **STALE** (7 days) — overridden by web-sourced $79.15 (July 13 2026, 06:40 UTC check) |
| DCOILWTICO | FRED (daily) | $69.60 | 2026-07-06 | **STALE** (7 days) — overridden by web-sourced $74.56 (July 13 2026) |
| INDPRO | FRED (monthly) | 102.65 | 2026-05-01 | **STALE** (73 days) — background only, not used in calculations |
| CPIAUCSL | FRED (monthly) | 333.979 (4.2% YoY) | 2026-05-01 | **STALE** (73 days) — May 2026 figure; June 2026 data due July 14 |
| T10YIE | FRED (daily) | 2.24% | 2026-07-10 | Valid (3 days old) |
| CBUAE Base Rate | CBUAE tool + web search (angelindubai.com, centralbank.ae) | 3.65% | 2026-07-13 | Valid — confirmed today; 214 consecutive unchanged days |
| EIBOR 3M | state.json baseline (CBUAE tool web fallback, July 10) | 3.900% | 2026-07-10 | **ESTIMATED** — no live 3M fixing found today; CBUAE overnight/DONIA/MLF rates confirmed unchanged (July 6 search), consistent with a flat 3M reading |
| OPEC basket | OPEC tool | null | N/A | **UNAVAILABLE** — scraper returned null; UAE exited OPEC+ May 2026 |
| UAE GDP | World Bank (NY.GDP.MKTP.CD) | $552.3bn | 2024 | Valid (structural reference) |
| UAE Industry % GDP | World Bank (NV.IND.TOTL.ZS) | 44.3% | 2024 | Valid (structural reference) |
| UAE CPI inflation | World Bank (FP.CPI.TOTL.ZG) | 1.25% | 2025 | Valid (structural reference) |
| Brent (web) | WebSearch: Bloomberg, tradingeconomics.com, investing.com | $79.02–79.22 | 2026-07-13 (06:40 UTC check) | Valid — intraday-flat vs. $79.11 baseline (05:58 UTC run) |
| Strait of Hormuz status | WebSearch: Bloomberg, Yahoo Finance, Wikipedia (2026 Strait of Hormuz crisis) | Iran claims closure "until further notice"; CENTCOM denies, reports additional strikes | 2026-07-13 | Valid |
| FOMC schedule/status | WebSearch: federalreserve.gov, CNBC (July 10 minutes) | Hold 3.50–3.75%, next decision July 29 | 2026-06-17 / 2026-07-10 | Valid |
| US June CPI release date | WebSearch: bls.gov, savingadvice.com | Release July 14, 08:30 ET | scheduled | Valid |
| Make it in Emirates AED 180bn | Prior-session web search (retained from 05:58 UTC run) | AED 180bn | 2026-07 | Valid — no new figure found this session |
| UAE production 3.8 mb/d | Reuters (retained from prior session) | 3.8 mb/d | 2026-07-06 | Valid — no update found this session |

---

## Methodology

**Same-day refresh scope:** This brief refreshes data ~23 minutes after the 06:18 UTC brief. No NEW signal met the Type A threshold; the only material update is the CENTCOM denial of Iran's Hormuz closure claim, which is a status escalation of a `[CONTINUING]` signal, not a new event, and is treated as such per the no-stale-headlines rule. All four required calculations were re-run in full per the CLAUDE.md same-day-refresh instruction, even though most inputs are unchanged or moved negligibly (Brent +$0.04 intraday).

**EIBOR estimation:** EIBOR 3M is estimated at 3.900%, carried from the state.json baseline established July 10, 2026. No live 3-month fixing was found in this session's search; CBUAE overnight (3.45%), DONIA (3.833%), and MLF/CMF (4.15%) rates were confirmed unchanged as of a July 6 source, consistent with — but not direct confirmation of — a flat 3M reading. The CBUAE base rate (3.65%) was reconfirmed July 13. This is the 3rd consecutive day the 3M estimate has been carried flat (streak began July 10).

**Stale FRED series overrides:** DCOILBRENTEU ($69.56, July 6) and DCOILWTICO ($69.60, July 6) are 7 days stale and are overridden by web-sourced figures ($79.15 and $74.56 respectively, checked July 13 06:40 UTC). FEDFUNDS (3.63%, June, 42 days stale) is assumed unchanged at the 3.50–3.75% target range per the June 17 FOMC decision. CPIAUCSL (May 2026, 73 days stale) is the last confirmed reading; June data is due July 14. INDPRO (May 2026, 73 days stale) is background only and not used in any calculation.

**OPEC basket:** The OPEC scraper returned null. The UAE formally exited OPEC+ effective May 1, 2026; UAE production is sourced from a retained Reuters figure (3.8 mb/d, July 6) with no update found this session.

**Operation 300bn methodology:** Gap-closed calculation uses (current − baseline) / (target − baseline) = (200 − 133) / (300 − 133) = 40.1%, not current/target (which incorrectly yields 66.7%). The AED 200bn milestone was confirmed May 4, 2026.

**Petrochemical pass-through:** Brent delta vs. the July 6 FRED baseline × 60% pass-through rate, applied to an estimated UAE petrochemical feedstock base of ~AED 17.5bn/year (industry estimate, unchanged from prior session).

**Hormuz probability scenarios:** Retained from the 05:58 UTC run's analytical estimate (35% partial/temporary, 40% sustained 2–4 weeks, 25% full escalation). The CENTCOM denial and continued strikes are a directional input toward the lower end of this range but are not yet reflected in a formal re-weighting, since Brent has not moved materially since the scenario was set.

**World Bank data:** All indicators reflect the most recent available year (2024 for GDP, industry %, FDI; 2025 for UAE CPI) and are used as structural reference figures only.
