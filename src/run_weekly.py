import argparse
import json

from .config import (
    EMAIL_PREVIEW_PATH,
    FORECAST_PATH,
    RECIPIENTS_RAW,
    parse_recipients,
)
from .data_sources import get_yahoo_weekly_data
from .email_builder import build_html, build_subject
from .email_sender import send_email
from .features import build_feature_table
from .llm_commentary import generate_commentary
from .model import predict_next_week, train_and_evaluate


def build_facts(df, forecast):
    latest = df.iloc[-1]

    def pct(name):
        value = latest.get(name)
        return None if value is None or value != value else round(float(value) * 100, 1)

    gdt = latest.get("gdt_change_pct")
    fertiliser = latest.get("fertiliser_yoy_change")

    return {
        "last_price_usd_cwt": forecast["last_price_usd_cwt"],
        "forecast_price_usd_cwt": forecast["forecast_price_usd_cwt"],
        "forecast_change_pct": forecast["forecast_change_pct"],
        "forecast_range_usd_cwt": forecast["forecast_range_usd_cwt"],
        "direction": forecast["direction"],
        "oil_week_change_pct": pct("oil_chg_1w"),
        "corn_week_change_pct": pct("corn_chg_1w"),
        "soybean_week_change_pct": pct("soybeans_chg_1w"),
        "wheat_week_change_pct": pct("wheat_chg_1w"),
        "butter_week_change_pct": pct("butter_chg_1w"),
        "cheese_week_change_pct": pct("cheese_chg_1w"),
        "natgas_week_change_pct": pct("natgas_chg_1w"),
        "milk_to_feed_ratio_change_pct": pct("milk_to_feed_chg_1w"),
        "eurusd_week_change_pct": pct("eurusd_chg_1w"),
        "nzdusd_week_change_pct": pct("nzdusd_chg_1w"),
        "gdt_latest_change_pct": None if gdt is None or gdt != gdt else round(float(gdt), 1),
        "gdt_available": bool(latest.get("gdt_available", False)),
        "fertiliser_year_on_year_change_pct": (
            None if fertiliser is None or fertiliser != fertiliser else round(float(fertiliser) * 100, 1)
        ),
        "munster_temperature_anomaly_c": (
            None if latest.get("munster_temp_anomaly") is None or latest.get("munster_temp_anomaly") != latest.get("munster_temp_anomaly")
            else round(float(latest["munster_temp_anomaly"]), 1)
        ),
        "munster_rain_anomaly_pct": (
            None if latest.get("munster_rain_anomaly") is None or latest.get("munster_rain_anomaly") != latest.get("munster_rain_anomaly")
            else round(float(latest["munster_rain_anomaly"]) * 100, 1)
        ),
        "model_beats_naive_baseline": forecast["beats_naive"],
    }


def run(train_only: bool = False, test_email: bool = False):
    print("Downloading market data...")
    market_data = get_yahoo_weekly_data(years=2)

    print("Building features...")
    df = build_feature_table(market_data)

    print("Training and evaluating model...")
    _, report = train_and_evaluate(df)
    print(json.dumps(report, indent=2))

    if train_only:
        print("Training complete.")
        return

    print("Generating forecast...")
    forecast = predict_next_week(df)
    FORECAST_PATH.write_text(json.dumps(forecast, indent=2))

    facts = build_facts(df, forecast)

    print("Generating commentary...")
    commentary = generate_commentary(facts)

    latest = df.iloc[-1]
    eurusd = float(latest["eurusd"])

    subject = build_subject(forecast)
    html = build_html(forecast, commentary, eurusd)

    EMAIL_PREVIEW_PATH.write_text(html)

    result = {
        "forecast": forecast,
        "facts": facts,
        "commentary": commentary,
        "subject": subject,
    }

    print(json.dumps(result, indent=2))

    if test_email:
        recipients = parse_recipients(RECIPIENTS_RAW)
        if not recipients:
            raise ValueError("No recipients configured in RECIPIENTS")

        # Send only to the first configured recipient during a test.
        response = send_email(subject, html, recipients[:1])
        print("Test email sent:", response)
        return

    recipients = parse_recipients(RECIPIENTS_RAW)
    if not recipients:
        raise ValueError("No recipients configured in RECIPIENTS")

    response = send_email(subject, html, recipients)
    print("Weekly email sent:", response)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-only", action="store_true")
    parser.add_argument("--test-email", action="store_true")
    args = parser.parse_args()

    run(train_only=args.train_only, test_email=args.test_email)
