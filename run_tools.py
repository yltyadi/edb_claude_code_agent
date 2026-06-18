#!/usr/bin/env python3
"""
EDB tool dispatcher — called by Claude Code via Bash.
Usage:
  python3 run_tools.py fred <SERIES_ID> [lookback_days]
  python3 run_tools.py worldbank <country_code> <indicator>
  python3 run_tools.py cbuae
  python3 run_tools.py opec

Prints JSON to stdout. Exits 0 on success, 1 on error.
"""

import json
import sys
from pathlib import Path

# Load .env from project root
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: run_tools.py <fred|worldbank|cbuae|opec> [args...]"}))
        sys.exit(1)

    tool = sys.argv[1].lower()

    if tool == "fred":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: run_tools.py fred <SERIES_ID> [lookback_days]"}))
            sys.exit(1)
        from tools.fred_api import get_fred_series
        series_id = sys.argv[2]
        lookback = int(sys.argv[3]) if len(sys.argv) > 3 else 90
        result = get_fred_series(series_id, lookback)
        print(json.dumps(result, default=str, indent=2))

    elif tool == "worldbank":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: run_tools.py worldbank <country_code> <indicator>"}))
            sys.exit(1)
        from tools.world_bank import get_world_bank_indicator
        result = get_world_bank_indicator(sys.argv[2], sys.argv[3])
        print(json.dumps(result, default=str, indent=2))

    elif tool == "cbuae":
        from tools.cbuae_scraper import scrape_cbuae_rates
        result = scrape_cbuae_rates()
        print(json.dumps(result, default=str, indent=2))

    elif tool == "opec":
        from tools.opec_scraper import scrape_opec_data
        result = scrape_opec_data()
        print(json.dumps(result, default=str, indent=2))

    else:
        print(json.dumps({"error": f"Unknown tool: {tool}. Choose: fred, worldbank, cbuae, opec"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
