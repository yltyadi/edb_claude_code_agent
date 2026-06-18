import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
})

_CBUAE_URLS = [
    "https://www.centralbank.ae/en/our-operations/monetary-policy-and-domestic-markets/",
    "https://www.centralbank.ae/en/monetary-policy/",
    "https://www.centralbank.ae/en/",
]


def scrape_cbuae_rates() -> dict:
    """
    Fetch current CBUAE Base Rate and latest policy statement.
    Tries multiple URL patterns; falls back to web search on repeated failure.
    Returns: {base_rate, rate_date, source_url, confidence, policy_summary, fetched_at}
    """
    fetched_at = datetime.now(timezone.utc).isoformat()

    for url in _CBUAE_URLS:
        result = _try_scrape_url(url, fetched_at)
        if result.get("base_rate"):
            return result

    # Final fallback: web search
    return _fallback_web_search(fetched_at)


def _try_scrape_url(url: str, fetched_at: str) -> dict:
    try:
        resp = _SESSION.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return {"error": str(e), "url": url}

    soup = BeautifulSoup(resp.text, "lxml")
    text = soup.get_text(separator=" ", strip=True)

    base_rate = _extract_rate(text)
    rate_date = _extract_date(text)
    policy_summary = _extract_policy_summary(soup, text)

    return {
        "base_rate": base_rate,
        "rate_date": rate_date,
        "source_url": url,
        "confidence": "high" if base_rate else "low",
        "policy_summary": policy_summary,
        "fetched_at": fetched_at,
    }


def _extract_rate(text: str):
    """Extract a base rate percentage from page text."""
    # Match patterns like "4.40%", "Base Rate: 4.40", "rate of 4.40 per cent"
    patterns = [
        r"(?:base rate|base lending rate|policy rate)[^\d]{0,30}(\d+\.\d+)\s*%",
        r"(\d+\.\d+)\s*%\s*(?:per annum|p\.a\.|base rate)",
        r"rate\s+(?:of\s+)?(\d+\.\d+)\s*(?:%|percent|per cent)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                rate = float(match.group(1))
                if 0.0 < rate < 25.0:  # Sanity check
                    return rate
            except ValueError:
                continue
    return None


def _extract_date(text: str):
    """Extract the most recent date mentioned near a rate decision."""
    patterns = [
        r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})",
        r"(\d{4}-\d{2}-\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _extract_policy_summary(soup: BeautifulSoup, text: str) -> str:
    """Extract a short policy statement summary."""
    # Look for press release or statement blocks
    for selector in [".press-release", ".policy-statement", "article", ".content-area"]:
        el = soup.select_one(selector)
        if el:
            snippet = el.get_text(separator=" ", strip=True)[:600]
            if len(snippet) > 100:
                return snippet

    # Fallback: find sentences mentioning monetary policy
    sentences = re.split(r'(?<=[.!?])\s+', text)
    relevant = [s for s in sentences if any(
        kw in s.lower() for kw in ["monetary policy", "base rate", "interest rate", "inflation"]
    )]
    return " ".join(relevant[:3])[:600] if relevant else ""


def _fallback_web_search(fetched_at: str) -> dict:
    """Use web search as last resort when direct scraping fails."""
    from tools.web_search import web_search
    month_year = datetime.now().strftime("%B %Y")
    results = web_search(f"CBUAE base rate current {month_year}", max_results=3)

    combined_text = " ".join(r.get("snippet", "") for r in results)
    base_rate = _extract_rate(combined_text)
    rate_date = _extract_date(combined_text)

    return {
        "base_rate": base_rate,
        "rate_date": rate_date,
        "source_url": results[0].get("url", "") if results else "",
        "confidence": "medium" if base_rate else "low",
        "policy_summary": combined_text[:600],
        "fetched_at": fetched_at,
        "source_method": "web_search_fallback",
    }
