import pandas as pd

from .data_sources import get_fertiliser_data, get_latest_gdt_change, get_open_meteo_weather


def build_feature_table(market_data: pd.DataFrame) -> pd.DataFrame:
    df = market_data.copy()
    df = df.sort_index()

    for lag in [1, 2, 4, 8]:
        df[f"milk_lag_{lag}"] = df["milk"].shift(lag)

    df["milk_chg_1w"] = df["milk"].pct_change()
    df["milk_chg_2w"] = df["milk"].pct_change(2)
    df["milk_chg_4w"] = df["milk"].pct_change(4)
    df["milk_chg_8w"] = df["milk"].pct_change(8)

    df["milk_roll_mean_4w"] = df["milk"].shift(1).rolling(4).mean()
    df["milk_roll_std_4w"] = df["milk"].pct_change().shift(1).rolling(4).std()
    df["milk_trend_4w"] = df["milk"] / df["milk"].shift(4) - 1

    for col in ["oil", "corn", "soybeans", "wheat", "butter", "cheese", "natgas", "eurusd", "nzdusd"]:
        df[f"{col}_chg_1w"] = df[col].pct_change()
        df[f"{col}_chg_4w"] = df[col].pct_change(4)

    # Milk-to-feed ratio: milk price relative to feed costs (corn + soybeans)
    df["milk_to_feed"] = df["milk"] / (df["corn"] + df["soybeans"])
    df["milk_to_feed_chg_1w"] = df["milk_to_feed"].pct_change()
    df["milk_to_feed_chg_4w"] = df["milk_to_feed"].pct_change(4)

    df["month"] = df.index.month
    df["iso_week"] = df.index.isocalendar().week.astype(int)

    weather = get_open_meteo_weather()
    df = df.join(weather, how="left")

    gdt = get_latest_gdt_change()
    df["gdt_change_pct"] = gdt["gdt_change_pct"]
    df["gdt_available"] = gdt["gdt_available"]

    fertiliser = get_fertiliser_data()
    fertiliser = fertiliser[["fertiliser_yoy_change"]].copy()
    fertiliser.index = fertiliser.index.to_period("M").to_timestamp("M")

    df = df.copy()
    df["month_end"] = df.index.to_period("M").to_timestamp("M")
    df = df.merge(
        fertiliser,
        left_on="month_end",
        right_index=True,
        how="left",
    )
    df = df.drop(columns=["month_end"])

    df["fertiliser_yoy_change"] = df["fertiliser_yoy_change"].ffill()

    return df


FEATURE_COLUMNS = [
    "milk_lag_1",
    "milk_lag_2",
    "milk_lag_4",
    "milk_lag_8",
    "milk_chg_1w",
    "milk_chg_2w",
    "milk_chg_4w",
    "milk_chg_8w",
    "milk_roll_mean_4w",
    "milk_roll_std_4w",
    "milk_trend_4w",
    "oil_chg_1w",
    "oil_chg_4w",
    "corn_chg_1w",
    "corn_chg_4w",
    "soybeans_chg_1w",
    "soybeans_chg_4w",
    "wheat_chg_1w",
    "wheat_chg_4w",
    "butter_chg_1w",
    "butter_chg_4w",
    "cheese_chg_1w",
    "cheese_chg_4w",
    "natgas_chg_1w",
    "natgas_chg_4w",
    "milk_to_feed",
    "milk_to_feed_chg_1w",
    "milk_to_feed_chg_4w",
    "eurusd_chg_1w",
    "eurusd_chg_4w",
    "nzdusd_chg_1w",
    "nzdusd_chg_4w",
    "month",
    "iso_week",
    "gdt_change_pct",
    "fertiliser_yoy_change",
]

WEATHER_FEATURES = [
        "munster_temp_anomaly",
        "munster_rain_anomaly",
        "northern_ireland_temp_anomaly",
        "northern_ireland_rain_anomaly",
        "netherlands_temp_anomaly",
        "netherlands_rain_anomaly",
        "waikato_nz_temp_anomaly",
        "waikato_nz_rain_anomaly",
    ]

FEATURE_COLUMNS += WEATHER_FEATURES


def make_supervised(df: pd.DataFrame):
    data = df.copy()
    data["target"] = data["milk"].shift(-1)

    usable = data.dropna(subset=["target"])

    missing = [col for col in FEATURE_COLUMNS if col not in usable.columns]
    if missing:
        raise RuntimeError(f"Missing expected feature columns: {missing}")

    X = usable[FEATURE_COLUMNS].fillna(0)
    y = usable["target"]
    return X, y, usable


def latest_prediction_row(df: pd.DataFrame) -> pd.DataFrame:
    row = df.iloc[[-1]][FEATURE_COLUMNS].fillna(0)
    return row
