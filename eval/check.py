#!/usr/bin/env python3
"""
Run automated rubric checks on a brief file.
Prints JSON to stdout — called by the eval-brief skill.

Usage:
  python3 eval/check.py <brief_path>
  python3 eval/check.py outputs/edb_brief_2026-06-17_0700.md
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.evaluator import AutomatedEvaluator


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: check.py <brief_path>"}))
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(json.dumps({"error": f"File not found: {path}"}))
        sys.exit(1)

    text = path.read_text(encoding="utf-8")
    checks = AutomatedEvaluator().run(text)

    passed = sum(1 for c in checks if c.passed)
    total = len(checks)

    print(json.dumps({
        "path":   str(path),
        "passed": passed,
        "total":  total,
        "score_pct": round(passed / total * 100, 1),
        "checks": [
            {"id": c.id, "name": c.name, "passed": c.passed, "evidence": c.evidence}
            for c in checks
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
