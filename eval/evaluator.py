"""
EDB Macro Agent — Automated Evaluator

Runs structural/regex checks from the rubric against a brief string.
LLM-dimension scoring is handled by Claude Code itself (see eval-brief skill).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from eval.rubric import AUTOMATED_CHECKS


@dataclass
class CheckResult:
    id: str
    name: str
    passed: bool
    evidence: str = ""  # matched snippet (first 120 chars) if passed


class AutomatedEvaluator:
    """Runs all AUTOMATED_CHECKS against a brief string."""

    def run(self, brief_text: str) -> list[CheckResult]:
        results = []
        for check in AUTOMATED_CHECKS:
            m = re.search(check["pattern"], brief_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if m:
                snippet = m.group(0)[:120].replace("\n", " ")
                results.append(CheckResult(check["id"], check["name"], True, snippet))
            else:
                results.append(CheckResult(check["id"], check["name"], False))
        return results
