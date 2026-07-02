"""
EDB Macro Agent — Evaluation Rubric  (v2)

Two scoring layers:
  1. AUTOMATED_CHECKS  — 20 regex / structural assertions (binary, each 1 pt)
  2. LLM_DIMENSIONS    — 7 LLM-as-judge dimensions (1–5, weighted)

Final score = auto_pct * AUTO_WEIGHT + llm_pct * LLM_WEIGHT  (→ 0–100)

Design goal: a fully correct v1 brief scores ~82/100; a v2 brief with state.json
and trend language scores ~90–95; a perfect brief scores 100.
"""

AUTO_WEIGHT = 0.40
LLM_WEIGHT  = 0.60

# ── 20 automated checks ───────────────────────────────────────────────────
AUTOMATED_CHECKS = [
    # ── structure (required sections) ─────────────────────────────────
    {
        "id": "has_exec_brief",
        "name": "Executive Brief (Type A) section present",
        "pattern": r"(?im)^##\s+(executive\s+brief|type\s+a)",
    },
    {
        "id": "has_credit_alert",
        "name": "Credit Alert (Type B) section present",
        "pattern": r"(?im)^##\s+(credit\s+(team\s+)?alert|type\s+b)",
    },
    {
        "id": "has_stakeholder_bulletin",
        "name": "Stakeholder Bulletin (Type C) section present",
        "pattern": r"(?im)^##\s+(stakeholder\s+bulletin|type\s+c)",
    },
    {
        "id": "has_sector_matrix",
        "name": "Sector impact matrix (all 5 sectors) present",
        "pattern": r"(?is)advanced\s+technology.{0,800}manufacturing.{0,800}healthcare.{0,800}renewables.{0,800}food\s+security",
    },
    {
        "id": "has_key_number",
        "name": "Key number field present",
        "pattern": r"(?i)\*\*key\s+number",
    },
    {
        "id": "has_watchlist",
        "name": "Watch list (next 72 h) present",
        "pattern": r"(?i)watch\s+list",
    },
    {
        "id": "has_action_flag",
        "name": "Action flag (MONITOR/REVIEW/ESCALATE) present",
        "pattern": r"\b(MONITOR|REVIEW|ESCALATE)\b",
    },
    # ── calculations & data ──────────────────────────────────────────
    {
        "id": "has_calculation_block",
        "name": "Python calculation output block (with AED) present",
        "pattern": r"```[\s\S]*?AED[\s\S]*?```",
    },
    {
        "id": "has_eibor_sensitivity",
        "name": "EIBOR ±25bps scenario calculation present",
        # checks for ±25bps scenario; AED proximity not required (calc-block check covers that)
        "pattern": r"(?i)\b(EIBOR.{0,300}[+\-]25\s*bps|[+\-]25\s*bps.{0,300}EIBOR|plus\s+25\s*(bps|basis)|minus\s+25\s*(bps|basis))",
    },
    {
        "id": "has_oil_revenue_calc",
        "name": "Oil revenue / fiscal impact calculation present",
        # matches "oil revenue", "fiscal impact", "revenue impact", "oil fiscal", "fiscal buffer", "fiscal cushion"
        "pattern": r"(?i)(oil\s+revenue|oil\s+fiscal|fiscal.{0,20}impact|fiscal\s+buffer|fiscal\s+cushion|revenue\s+impact).{0,100}AED",
    },
    # ── sourcing & integrity ─────────────────────────────────────────
    {
        "id": "has_sources",
        "name": "Sources section present",
        "pattern": r"(?i)(sources?:|\\*sources)",
    },
    {
        "id": "has_methodology_note",
        "name": "Methodology / data-gap note present",
        "pattern": r"(?i)(methodology|data\s+gap|data\s+note)",
    },
    # ── peg chain & EIBOR ────────────────────────────────────────────
    {
        "id": "mentions_eibor",
        "name": "EIBOR explicitly mentioned",
        "pattern": r"\bEIBOR\b",
    },
    {
        "id": "peg_chain_traced",
        "name": "Full peg chain traced (Fed→CBUAE→EIBOR→portfolio)",
        "pattern": r"(?is)(fed|federal\s+reserve).{0,200}cbuae.{0,200}eibor.{0,200}(portfolio|loan|sme|debt)",
    },
    # ── header metadata ──────────────────────────────────────────────
    {
        "id": "has_date_header",
        "name": "Date header present",
        "pattern": r"(?i)\*\*date[\*:]",
    },
    {
        "id": "has_signals_processed",
        "name": "Signals processed count in header",
        "pattern": r"(?i)\*\*signals\s+processed",
    },
    # ── analytical quality ───────────────────────────────────────────
    {
        "id": "has_scenario_analysis",
        "name": "Dual-scenario analysis (base case vs reversal) present",
        "pattern": r"(?is)(structural.{0,500}reversal|base\s+case.{0,200}event\s+risk|base\s+case.{0,200}reversal)",
    },
    {
        "id": "has_operation_300bn_progress",
        "name": "Operation 300bn progress percentage computed",
        "pattern": r"(?i)(66\.7|two.thirds|operation 300bn.{0,80}\d+\.?\d*\s*%|\d+\.?\d*\s*%\s+of\s+(the\s+)?300bn)",
    },
    # ── state & version (rewards v2+) ────────────────────────────────
    {
        "id": "has_prior_state_reference",
        "name": "References prior-run baseline (state.json / streak / unchanged N days)",
        "pattern": r"(?i)(state\.json|prior\s+run|last\s+brief|unchanged\s+for\s+\d+|consecutive\s+(fed\s+)?(hold|meeting|session|session)|\d+\s+(consecutive|straight)\s+(session|day|hold|meeting))",
    },
    {
        "id": "has_version_header",
        "name": "Agent version declared in brief header",
        "pattern": r"(?i)(\*\*agent\s+version|\*\*version[:\*]|version[:\s]+v\d\b)",
    },
]

# ── 7 LLM-judged dimensions ───────────────────────────────────────────────
LLM_DIMENSIONS = [
    {
        "id": "mandate_relevance",
        "name": "Mandate Relevance",
        "weight": 0.20,
        "description": (
            "Every signal is mapped to ≥1 of EDB's five sectors with a specific quantified "
            "impact for that sector. Every row in the sector matrix names a direction and urgency "
            "justified by data — placeholder rows like 'no direct signal this cycle' without "
            "any sector-specific implication are penalised. Zero generic market commentary."
        ),
        "scale": {
            5: "All signals sector-mapped with quantified impact; every matrix row data-justified; zero generic filler",
            4: "Most signals sector-mapped; 1–2 matrix rows thin or placeholder; negligible generic filler",
            3: "Roughly half sector-mapped; some matrix rows are placeholders; noticeable generic passages",
            2: "Sector mapping superficial; mostly generic; matrix rows not justified by data",
            1: "No EDB mandate framing",
        },
    },
    {
        "id": "data_grounding",
        "name": "Data Grounding & Source Citation",
        "weight": 0.16,
        "description": (
            "Every number traces to a named authoritative source. Live-fetched data is preferred "
            "over estimated; where estimation is used the estimation basis must be stated prominently "
            "— not only in a methodology appendix. EIBOR specifically: must be either fetched from "
            "the CBUAE live EIBOR page or labeled as an estimate with the spread basis stated. "
            "Tool failures must name every affected series."
        ),
        "scale": {
            5: "All numbers sourced to named authorities; EIBOR basis prominently stated; all tool failures named; no hallucinations",
            4: "Most numbers sourced; EIBOR estimate disclosed but not prominently; minor gaps",
            3: "Some numbers unsourced; EIBOR treatment inconsistent; moderate hallucination risk",
            2: "Many unsourced numbers; EIBOR used without disclosure; likely hallucinations",
            1: "No sourcing; numbers appear invented",
        },
    },
    {
        "id": "quantitative_accuracy",
        "name": "Quantitative Accuracy & Calculation Discipline",
        "weight": 0.16,
        "description": (
            "All four required calculations must be present and correct: "
            "(1) EIBOR sensitivity for reference loan with ±25bps and ±50bps scenarios; "
            "(2) oil revenue impact in both USD and AED with explicit FX conversion step shown; "
            "(3) petrochemical input-cost pass-through; "
            "(4) Operation 300bn annual run-rate required. "
            "Key input rates (especially EIBOR) must be either live-fetched or the estimation basis "
            "stated. All figures must be internally consistent (e.g. ADS = quarterly × 4)."
        ),
        "scale": {
            5: "All four calculations present and correct; scenarios complete; FX step shown; EIBOR basis stated; internally consistent",
            4: "Three of four present and correct; one minor gap or missing FX step",
            3: "Two calculations present; errors or missing scenarios; EIBOR basis not stated",
            2: "One calculation; numbers stated without derivation",
            1: "No calculations",
        },
    },
    {
        "id": "structure_completeness",
        "name": "Output Structure Completeness",
        "weight": 0.12,
        "description": (
            "Type A: headline, sector matrix with 5 data-justified rows, key number in AED, 72h watchlist with ≥3 named events. "
            "Type B: ≥2 signals each with named exposure, calculation block, action flag with rationale. "
            "Type C: What happened / What it means / What to consider, each ≥2 sentences."
        ),
        "scale": {
            5: "All three types with every sub-field substantive and complete",
            4: "All three types present; 1–2 sub-fields thin",
            3: "Two types present or all three with several empty fields",
            2: "One type present",
            1: "No structured sections",
        },
    },
    {
        "id": "action_specificity",
        "name": "Action Specificity",
        "weight": 0.12,
        "description": (
            "Each action flag (MONITOR/REVIEW/ESCALATE) must name: the specific EDB team or "
            "portfolio segment affected, a concrete trigger condition or threshold, and a "
            "reassessment milestone. Watch-list items must name a specific event with an "
            "estimated time window — not vague 'watch for developments' filler."
        ),
        "scale": {
            5: "Every flag names team, threshold, and milestone; watchlist items are specific events with times",
            4: "Flags name team and threshold; one watchlist item is vague",
            3: "Flags present with generic rationales; watchlist items partially specific",
            2: "Flags present but no team/threshold/milestone; watchlist is filler",
            1: "No action guidance",
        },
    },
    {
        "id": "data_integrity",
        "name": "Data Integrity & Gap Disclosure",
        "weight": 0.12,
        "description": (
            "Every input used in a calculation must be either live-fetched or disclosed as an "
            "estimate with its estimation method. Stale data must be flagged with its vintage year. "
            "Tool failures must be listed by series name. The EIBOR estimate specifically must be "
            "labeled in the calculation block itself (not only in a methodology note). "
            "No data is used silently."
        ),
        "scale": {
            5: "All calculation inputs disclosed; EIBOR labeled in calc block; stale data vintaged; failures listed by name; no silent estimates",
            4: "Most inputs disclosed; EIBOR disclosed in methodology but not in calc block",
            3: "Some disclosure; EIBOR or other key inputs used silently",
            2: "Gaps not disclosed; estimated inputs used as if live",
            1: "No disclosure; clear hallucinations",
        },
    },
    {
        "id": "trend_continuity",
        "name": "Trend & Continuity",
        "weight": 0.12,
        "description": (
            "The brief should use prior-run baselines from state.json to add temporal depth: "
            "specific streak counts (N consecutive Fed holds, EIBOR unchanged for N days, "
            "Brent's 4th consecutive declining session), delta from yesterday's key number, "
            "and at least one signal framed cumulatively rather than as a static snapshot. "
            "Without state.json this dimension is structurally limited to a maximum of 2."
        ),
        "scale": {
            5: "Multiple trend observations with specific numeric baselines from state.json; today's key number compared to prior run; at least one cumulative framing",
            4: "One specific trend observation with a numeric baseline from state.json",
            3: "Trend direction noted but no specific prior-run numeric baseline",
            2: "Some period comparison (e.g. May avg vs today) but no state.json streak data",
            1: "Pure static snapshot; no temporal dimension",
        },
    },
]

# ── convenience ────────────────────────────────────────────────────────────
DIMENSION_IDS     = [d["id"]     for d in LLM_DIMENSIONS]
DIMENSION_NAMES   = [d["name"]   for d in LLM_DIMENSIONS]
DIMENSION_WEIGHTS = {d["id"]: d["weight"] for d in LLM_DIMENSIONS}
AUTO_CHECK_IDS    = [c["id"]     for c in AUTOMATED_CHECKS]

assert abs(sum(DIMENSION_WEIGHTS.values()) - 1.0) < 1e-9, "weights must sum to 1.0"
