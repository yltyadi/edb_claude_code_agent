EDB_SECTORS = {
    "advanced_technology": {
        "label": "Advanced Technology",
        "keywords": ["semiconductor", "AI", "artificial intelligence", "software", "digital", "tech"],
        "fred_proxies": ["INDPRO"],
    },
    "manufacturing": {
        "label": "Manufacturing",
        "keywords": ["manufacturing", "industrial", "capex", "factory", "production", "supply chain"],
        "fred_proxies": ["INDPRO", "DCOILBRENTEU"],
    },
    "healthcare": {
        "label": "Healthcare",
        "keywords": ["healthcare", "medical", "pharmaceutical", "hospital", "biotech"],
        "fred_proxies": [],
    },
    "renewables": {
        "label": "Renewables",
        "keywords": ["solar", "wind", "renewable", "green hydrogen", "energy transition", "clean energy"],
        "fred_proxies": ["DCOILBRENTEU"],
    },
    "food_security": {
        "label": "Food Security",
        "keywords": ["food", "agriculture", "commodity", "grain", "wheat", "supply chain", "agri"],
        "fred_proxies": [],
    },
}

REFERENCE_LOAN = {
    "principal_aed": 5_000_000,
    "tenor_years": 7,
    "payments_per_year": 4,
    "spread_bps": 200,
}

THRESHOLDS = {
    "oil_price_move_pct": 2.0,
    "rate_change_bps": 25,
    "fed_signal_keywords": ["rate decision", "fomc", "federal reserve", "powell", "basis points"],
    "cbuae_signal_keywords": ["cbuae", "central bank uae", "base rate", "monetary policy"],
}
