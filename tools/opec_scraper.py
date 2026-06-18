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

_OPEC_URLS = [
    "https://www.opec.org/opec_web/en/press_room/press_releases.htm",
    "https://www.opec.org/opec_web/en/publications/338.htm",
    "https://www.opec.org/opec_web/en/",
]


def scrape_opec_data() -> dict:
    """
    Fetch latest OPEC oil market data: basket price, UAE production quota,
    any quota change announcements. Falls back to web search on failure.
    Returns: {opec_basket_price, uae_production_quota, latest_report_date,
              key_finding, source_url, fetched_at}
    """
    fetched_at = datetime.now(timezone.utc).isoformat()

    for url in _OPEC_URLS:
        result = _try_scrape_url(url, fetched_at)
        if result.get("opec_basket_price") or result.get("key_finding"):
            return result

    return _fallback_web_search(fetched_at)


def _try_scrape_url(url: str, fetched_at: str) -> dict:
    try:
        resp = _SESSION.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return {"error": str(e), "url": url}

    soup = BeautifulSoup(resp.text, "lxml")
    text = soup.get_text(separator=" ", strip=True)

    basket_price = _extract_basket_price(text)
    uae_quota = _extract_uae_quota(text)
    report_date = _extract_date(text)
    key_finding = _extract_key_finding(soup, text)

    return {
        "opec_basket_price": basket_price,
        "uae_production_quota": uae_quota,
        "latest_report_date": report_date,
        "key_finding": key_finding,
        "source_url": url,
        "fetched_at": fetched_at,
    }


def _extract_basket_price(text: str):
    """Extract OPEC Reference Basket price in USD/barrel."""
    patterns = [
        r"(?:OPEC\s+)?(?:reference\s+)?basket\s+(?:price\s+)?(?:stood\s+at\s+|was\s+|at\s+)?\$?(\d+\.?\d*)\s*(?:per\s+barrel|/\s*bbl|USD)",
        r"\$(\d+\.?\d*)\s*(?:per\s+barrel|/\s*bbl)",
        r"ORB[^\d]{0,20}(\d+\.?\d*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                price = float(match.group(1))
                if 20.0 < price < 300.0:  # Sanity check
                    return price
            except ValueError:
                continue
    return None


def _extract_uae_quota(text: str):
    """Extract UAE production quota in kb/d or mb/d."""
    patterns = [
        r"UAE[^\d]{0,50}(\d[\d,]*\.?\d*)\s*(?:kb/d|thousand barrels per day|mb/d|million barrels)",
        r"United Arab Emirates[^\d]{0,50}(\d[\d,]*\.?\d*)\s*(?:kb/d|mb/d|thousand|million)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                val_str = match.group(1).replace(",", "")
                return float(val_str)
            except ValueError:
                continue
    return None


def _extract_date(text: str):
    patterns = [
        r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
        r"(\d{4}-\d{2}-\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _extract_key_finding(soup: BeautifulSoup, text: str) -> str:
    """Extract a summary of the most important OPEC finding."""
    # Look for press release headlines or content blocks
    for selector in ["h1", "h2", ".press-release-title", ".news-title", "article"]:
        elements = soup.select(selector)
        for el in elements[:3]:
            snippet = el.get_text(strip=True)
            if len(snippet) > 30:
                return snippet[:400]

    # Fallback: first substantive paragraph
    sentences = re.split(r'(?<=[.!?])\s+', text)
    relevant = [s for s in sentences if any(
        kw in s.lower() for kw in ["production", "output", "barrel", "quota", "opec+", "supply"]
    )]
    return " ".join(relevant[:3])[:400] if relevant else text[:400]


def _fallback_web_search(fetched_at: str) -> dict:
    """Use web search as last resort when direct scraping fails."""
    from tools.web_search import web_search
    month_year = datetime.now().strftime("%B %Y")
    results = web_search(
        f"OPEC oil market report {month_year} UAE production basket price",
        max_results=5,
    )

    combined_text = " ".join(r.get("snippet", "") for r in results)
    basket_price = _extract_basket_price(combined_text)
    uae_quota = _extract_uae_quota(combined_text)
    report_date = _extract_date(combined_text)

    return {
        "opec_basket_price": basket_price,
        "uae_production_quota": uae_quota,
        "latest_report_date": report_date,
        "key_finding": combined_text[:400] if combined_text else "No OPEC data retrieved",
        "source_url": results[0].get("url", "") if results else "",
        "fetched_at": fetched_at,
        "source_method": "web_search_fallback",
    }
