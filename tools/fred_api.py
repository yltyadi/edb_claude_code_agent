import os
from datetime import datetime, timedelta

SERIES_TO_FETCH = {
    "FEDFUNDS":     "Fed Funds Rate (monthly, %)",
    "DGS10":        "10-Year Treasury Yield (daily, %)",
    "DCOILBRENTEU": "Brent Crude Oil (daily, USD/barrel)",
    "DCOILWTICO":   "WTI Crude Oil (daily, USD/barrel)",
    "INDPRO":       "US Industrial Production Index (monthly)",
    "CPIAUCSL":     "US CPI All Items (monthly)",
    "T10YIE":       "10-Year Breakeven Inflation Rate (daily, %)",
}


def _get_fred_client():
    from fredapi import Fred
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise ValueError("FRED_API_KEY not set in environment")
    return Fred(api_key=api_key)


def get_fred_series(series_id: str, lookback_days: int = 90) -> dict:
    """
    Fetch a FRED series. Returns dict with latest value, previous value,
    change, change_pct, date, description. Handles missing series gracefully.
    """
    try:
        fred = _get_fred_client()
    except ValueError as e:
        return {"error": str(e), "series_id": series_id}

    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        series = fred.get_series(series_id, observation_start=start_date.strftime("%Y-%m-%d"))
        series = series.dropna()

        if series.empty:
            return {"error": "No data returned", "series_id": series_id}

        latest_value = float(series.iloc[-1])
        latest_date = series.index[-1].strftime("%Y-%m-%d")
        description = SERIES_TO_FETCH.get(series_id, series_id)

        result = {
            "series_id": series_id,
            "description": description,
            "latest_value": latest_value,
            "latest_date": latest_date,
            "unit": _infer_unit(series_id),
            "frequency": _infer_frequency(series_id),
        }

        # Compute change vs previous observation
        if len(series) >= 2:
            previous_value = float(series.iloc[-2])
            change = latest_value - previous_value
            change_pct = (change / previous_value * 100) if previous_value != 0 else 0
            result["previous_value"] = previous_value
            result["previous_date"] = series.index[-2].strftime("%Y-%m-%d")
            result["change"] = round(change, 4)
            result["change_pct"] = round(change_pct, 4)

        # Flag stale data (>30 days old for time-sensitive series)
        days_old = (datetime.now() - series.index[-1].to_pydatetime().replace(tzinfo=None)).days
        if days_old > 30 and series_id in ("FEDFUNDS", "DGS10", "DCOILBRENTEU", "DCOILWTICO"):
            result["staleness_warning"] = f"Data is {days_old} days old — flag as potentially stale"

        return result

    except Exception as e:
        return {"error": str(e), "series_id": series_id}


def get_all_key_series() -> dict:
    """Fetch all series in SERIES_TO_FETCH. Logs failures but continues."""
    results = {}
    for series_id in SERIES_TO_FETCH:
        results[series_id] = get_fred_series(series_id)
    return results


def _infer_unit(series_id: str) -> str:
    unit_map = {
        "FEDFUNDS": "percent",
        "DGS10": "percent",
        "DCOILBRENTEU": "USD/barrel",
        "DCOILWTICO": "USD/barrel",
        "INDPRO": "index (2017=100)",
        "CPIAUCSL": "index (1982-84=100)",
        "T10YIE": "percent",
    }
    return unit_map.get(series_id, "")


def _infer_frequency(series_id: str) -> str:
    freq_map = {
        "FEDFUNDS": "monthly",
        "DGS10": "daily",
        "DCOILBRENTEU": "daily",
        "DCOILWTICO": "daily",
        "INDPRO": "monthly",
        "CPIAUCSL": "monthly",
        "T10YIE": "daily",
    }
    return freq_map.get(series_id, "unknown")
