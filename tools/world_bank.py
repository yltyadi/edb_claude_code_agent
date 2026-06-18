import requests

UAE_INDICATORS = {
    "NY.GDP.MKTP.CD":    "UAE GDP current USD",
    "NV.IND.TOTL.ZS":   "UAE industry value added % of GDP",
    "FP.CPI.TOTL.ZG":   "UAE CPI inflation annual %",
    "BX.KLT.DINV.CD.WD": "UAE FDI inflows USD",
    "NE.GDI.FTOT.ZS":   "UAE gross capital formation % of GDP",
}

_BASE_URL = "https://api.worldbank.org/v2"


def get_world_bank_indicator(country_code: str, indicator: str) -> dict:
    """
    Fetch from World Bank API. Returns latest 5 years of data.
    Note: World Bank data lags 1-2 years — always include the data year in output.
    """
    url = f"{_BASE_URL}/country/{country_code}/indicator/{indicator}"
    params = {"format": "json", "mrv": 5, "per_page": 10}

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        return {"error": str(e), "indicator": indicator, "country": country_code}

    if not isinstance(payload, list) or len(payload) < 2:
        return {"error": "Unexpected response structure", "indicator": indicator}

    metadata = payload[0]
    data_points = payload[1]

    if not data_points:
        return {"error": "No data points returned", "indicator": indicator, "country": country_code}

    # Filter out null values and sort by year descending
    observations = [
        {"year": int(d["date"]), "value": d["value"]}
        for d in data_points
        if d.get("value") is not None
    ]
    observations.sort(key=lambda x: x["year"], reverse=True)

    description = UAE_INDICATORS.get(indicator, indicator)
    result = {
        "indicator": indicator,
        "description": description,
        "country": country_code,
        "observations": observations,
    }

    if observations:
        latest = observations[0]
        result["latest_value"] = latest["value"]
        result["latest_year"] = latest["year"]
        result["data_lag_note"] = (
            f"Most recent data is from {latest['year']} — "
            "World Bank typically lags 1-2 years from current date"
        )

    return result


def get_all_uae_indicators() -> dict:
    """Fetch all UAE_INDICATORS. Returns dict keyed by indicator code."""
    results = {}
    for indicator in UAE_INDICATORS:
        results[indicator] = get_world_bank_indicator("AE", indicator)
    return results
