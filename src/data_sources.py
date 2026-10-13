import re
from datetime import UTC, datetime, timedelta
from io import BytesIO

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from .config import GDT_RESULTS_URL, WEATHER_LOCATIONS, WORLD_BANK_PINK_SHEET_URL, YAHOO_TICKERS


def get_yahoo_weekly_data(years: int = 2) -> pd.DataFrame:
    """Download daily Yahoo Finance data and convert it to weekly Sunday-ending data."""
    period = f"{years}y"
    frames = []

    for name, ticker in YAHOO_TICKERS.items():
        df = yf.download(
            ticker,
            period=period,
            interval="1d",
            auto_adjust=False,
            progress=False,
        )

        if df.empty:
            raise RuntimeError(f"No Yahoo Finance data returned for {ticker}")

        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        weekly = close.dropna().resample("W-SUN").last().rename(name).to_frame()
        frames.append(weekly)

    data = pd.concat(frames, axis=1)
    data = data.dropna()
    data.index.name = "week_end"
    return data


def get_open_meteo_weather() -> pd.DataFrame:
    """Return weekly rainfall and mean-temperature anomalies for selected dairy regions."""
    end_date = datetime.now(UTC).date()
    start_date = end_date - timedelta(days=730)

    rows = []

    for name, lat, lon in WEATHER_LOCATIONS:
        url = (
            "https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={lat}&longitude={lon}"
            f"&start_date={start_date}&end_date={end_date}"
            "&daily=temperature_2m_mean,precipitation_sum"
            "&timezone=UTC"
        )

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()

        daily = payload.get("daily", {})
        dates = pd.to_datetime(daily.get("time", []))
        temps = pd.Series(daily.get("temperature_2m_mean", []), index=dates)
        rain = pd.Series(daily.get("precipitation_sum", []), index=dates)

        weekly_temp = temps.resample("W-SUN").mean()
        weekly_rain = rain.resample("W-SUN").sum()

        normal_temp = weekly_temp.groupby(weekly_temp.index.isocalendar().week).transform("mean")
        normal_rain = weekly_rain.groupby(weekly_rain.index.isocalendar().week).transform("mean")

        temp_anomaly = weekly_temp - normal_temp
        rain_anomaly = (weekly_rain - normal_rain) / normal_rain.replace(0, np.nan)

        region = pd.DataFrame(
            {
                f"{name.lower().replace(' ', '_')}_temp_anomaly": temp_anomaly,
                f"{name.lower().replace(' ', '_')}_rain_anomaly": rain_anomaly,
            }
        )
        rows.append(region)

    weather = pd.concat(rows, axis=1)
    weather.index.name = "week_end"
    return weather


def get_fertiliser_data() -> pd.DataFrame:
    """Download the World Bank Pink Sheet and extract a fertiliser price index proxy."""
    response = requests.get(WORLD_BANK_PINK_SHEET_URL, timeout=60)
    response.raise_for_status()

    xls = pd.read_excel(BytesIO(response.content), sheet_name="Monthly Prices", skiprows=4)

    # The Pink Sheet layout can change. Find likely fertiliser columns dynamically.
    candidates = [
        col
        for col in xls.columns
        if isinstance(col, str)
        and any(
            word in col.lower()
            for word in ["fertilizer", "fertiliser", "phosphate", "potassium", "nitrogen", "urea", "dap"]
        )
    ]

    if not candidates:
        raise RuntimeError("Could not identify fertiliser columns in World Bank Pink Sheet")

    date_col = xls.columns[0]
    xls[date_col] = pd.to_datetime(xls[date_col], errors="coerce")
    xls = xls.dropna(subset=[date_col]).set_index(date_col)

    fertiliser = xls[candidates].apply(pd.to_numeric, errors="coerce").mean(axis=1)
    fertiliser = fertiliser.dropna().rename("fertiliser_index").to_frame()

    fertiliser["fertiliser_yoy_change"] = fertiliser["fertiliser_index"].pct_change(12)
    fertiliser.index.name = "month"
    return fertiliser


def get_latest_gdt_change() -> dict:
    """Scrape the public GDT results page for the latest reported percentage change.

    This is intentionally defensive: if GDT changes its page structure, the
    pipeline continues without GDT rather than failing.
    """
    try:
        response = requests.get(GDT_RESULTS_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        text = response.text

        matches = re.findall(r"([+-]?\d+(?:\.\d+)?)\s*%", text)
        values = [float(x) for x in matches if abs(float(x)) <= 25]

        if not values:
            return {"gdt_change_pct": None, "gdt_available": False}

        return {
            "gdt_change_pct": values[0],
            "gdt_available": True,
        }
    except Exception:
        return {"gdt_change_pct": None, "gdt_available": False}
