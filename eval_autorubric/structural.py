"""
Deterministic structural layer — the same 20 regex checks the OLD framework uses.

Kept deterministic (not LLM-judged): confirming that a literal '**Date:**' header
or a '## Type A' section exists is a job regex does more cheaply and more reliably
than an LLM. This is the shared 40% structural layer, identical across frameworks,
so any final-score gap is attributable purely to the LLM judging method.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.rubric import AUTOMATED_CHECKS  # noqa: E402

_FLAGS = re.IGNORECASE | re.MULTILINE | re.DOTALL


def run_structural(text: str) -> dict[str, bool]:
    """Return {check_id: passed} for all 20 structural checks."""
    if not text:
        return {c["id"]: False for c in AUTOMATED_CHECKS}
    return {c["id"]: bool(re.search(c["pattern"], text, _FLAGS)) for c in AUTOMATED_CHECKS}


def structural_pct(results: dict[str, bool]) -> float:
    """Fraction of structural checks passed (0.0-1.0)."""
    if not results:
        return 0.0
    return sum(1 for v in results.values() if v) / len(results)
