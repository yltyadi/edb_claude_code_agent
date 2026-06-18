import time
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


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search DuckDuckGo and return results with title, url, snippet.
    Falls back to DuckDuckGo HTML scraping if the JSON API returns thin results.
    Returns list of dicts: {title, url, snippet, fetched_at}
    """
    fetched_at = datetime.now(timezone.utc).isoformat()
    results = _ddg_json(query, max_results, fetched_at)
    if len(results) < 2:
        results = _ddg_html(query, max_results, fetched_at)
    return results[:max_results]


def _ddg_json(query: str, max_results: int, fetched_at: str) -> list[dict]:
    try:
        resp = _SESSION.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    results = []

    # Abstract result (top answer)
    if data.get("AbstractText") and data.get("AbstractURL"):
        results.append({
            "title": data.get("Heading", query),
            "url": data["AbstractURL"],
            "snippet": data["AbstractText"][:500],
            "fetched_at": fetched_at,
        })

    # Related topics
    for topic in data.get("RelatedTopics", []):
        if len(results) >= max_results:
            break
        if "Topics" in topic:
            # Sub-group — flatten
            for sub in topic["Topics"]:
                if len(results) >= max_results:
                    break
                url = sub.get("FirstURL", "")
                text = sub.get("Text", "")
                if url and text:
                    results.append({
                        "title": text[:80],
                        "url": url,
                        "snippet": text[:500],
                        "fetched_at": fetched_at,
                    })
        else:
            url = topic.get("FirstURL", "")
            text = topic.get("Text", "")
            if url and text:
                results.append({
                    "title": text[:80],
                    "url": url,
                    "snippet": text[:500],
                    "fetched_at": fetched_at,
                })

    return results


def _ddg_html(query: str, max_results: int, fetched_at: str) -> list[dict]:
    """Fallback: scrape DuckDuckGo HTML search results."""
    try:
        resp = _SESSION.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception:
        return [{"title": "Search unavailable", "url": "", "snippet": f"Could not search for: {query}", "fetched_at": fetched_at}]

    soup = BeautifulSoup(resp.text, "lxml")
    results = []
    for result in soup.select(".result"):
        if len(results) >= max_results:
            break
        title_el = result.select_one(".result__title a")
        snippet_el = result.select_one(".result__snippet")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        url = title_el.get("href", "")
        # DDG HTML wraps URLs — extract the actual URL from the redirect
        if "uddg=" in url:
            try:
                from urllib.parse import urlparse, parse_qs, unquote
                qs = parse_qs(urlparse(url).query)
                url = unquote(qs.get("uddg", [""])[0])
            except Exception:
                pass
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        results.append({
            "title": title,
            "url": url,
            "snippet": snippet[:500],
            "fetched_at": fetched_at,
        })
    return results


def fetch_article_text(url: str, max_chars: int = 3000) -> str:
    """
    Fetch and clean article text from a URL.
    Extracts <article>, <main>, or <p> tags; strips nav/footer/ads.
    Returns plain text truncated to max_chars.
    """
    if not url or not url.startswith("http"):
        return f"[Invalid URL: {url}]"

    try:
        resp = _SESSION.get(url, timeout=5, allow_redirects=True)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "html" not in content_type and "text" not in content_type:
            return f"[Non-HTML response: {content_type}]"
    except requests.exceptions.Timeout:
        return f"[Timeout fetching {url}]"
    except Exception as e:
        return f"[Error fetching {url}: {e}]"

    soup = BeautifulSoup(resp.text, "lxml")

    # Remove noise elements
    for tag in soup(["nav", "footer", "header", "aside", "script", "style",
                     "form", "noscript", "iframe", "ads", "advertisement"]):
        tag.decompose()
    for tag in soup.find_all(class_=lambda c: c and any(
        x in c.lower() for x in ["nav", "footer", "header", "sidebar", "ad-", "cookie"]
    )):
        tag.decompose()

    # Try progressively broader content containers
    for selector in ["article", "main", '[role="main"]', ".article-body", ".post-content", "body"]:
        container = soup.select_one(selector)
        if container:
            text = container.get_text(separator=" ", strip=True)
            # Collapse whitespace
            import re
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 200:
                return text[:max_chars]

    # Final fallback: all paragraphs
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 50]
    text = " ".join(paragraphs)
    import re
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars] if text else f"[No readable content at {url}]"
