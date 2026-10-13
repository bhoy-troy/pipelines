import json
from datetime import UTC, datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .config import BACKTEST_PATH, FEATURES_PATH, MODEL_PATH
from .features import FEATURE_COLUMNS, make_supervised


def build_model() -> Pipeline:
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=1.0)),
        ]
    )


def train_and_evaluate(df: pd.DataFrame):
    X, y, usable = make_supervised(df)

    if len(X) < 60:
        raise RuntimeError("Not enough historical weekly observations to train")

    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    model = build_model()
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    model_mae = float(mean_absolute_error(y_test, predictions))

    naive_predictions = X_test["milk_lag_1"]
    naive_mae = float(mean_absolute_error(y_test, naive_predictions))

    residuals = y_test - predictions
    residual_std = float(np.std(residuals)) if len(residuals) > 1 else 0.25

    final_model = build_model()
    final_model.fit(X, y)

    joblib.dump(
        {
            "model": final_model,
            "feature_columns": FEATURE_COLUMNS,
            "trained_at": datetime.now(UTC).isoformat(),
            "model_mae": model_mae,
            "naive_mae": naive_mae,
            "residual_std": residual_std,
        },
        MODEL_PATH,
    )

    report = {
        "trained_at": datetime.now(UTC).isoformat(),
        "observations": int(len(X)),
        "test_observations": int(len(X_test)),
        "model_mae_usd_cwt": round(model_mae, 4),
        "naive_mae_usd_cwt": round(naive_mae, 4),
        "beats_naive": bool(model_mae < naive_mae),
        "residual_std_usd_cwt": round(residual_std, 4),
    }

    BACKTEST_PATH.write_text(json.dumps(report, indent=2))
    return final_model, report


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError("Model not found. Run: python -m src.run_weekly --train-only")
    return joblib.load(MODEL_PATH)


def predict_next_week(df: pd.DataFrame):
    bundle = load_model()
    model = bundle["model"]
    feature_columns = bundle["feature_columns"]
    residual_std = bundle["residual_std"]

    latest = df.iloc[[-1]]
    X_next = latest[feature_columns].fillna(0)

    prediction = float(model.predict(X_next)[0])
    last_price = float(latest["milk"].iloc[0])
    change = prediction - last_price
    change_pct = change / last_price * 100

    if abs(change_pct) < 0.35:
        direction = "stable"
    elif change > 0:
        direction = "up"
    else:
        direction = "down"

    lower = prediction - residual_std
    upper = prediction + residual_std

    forecast = {
        "generated_at": datetime.now(UTC).isoformat(),
        "week_end": str(latest.index[0].date()),
        "last_price_usd_cwt": round(last_price, 2),
        "forecast_price_usd_cwt": round(prediction, 2),
        "forecast_change_usd_cwt": round(change, 2),
        "forecast_change_pct": round(change_pct, 2),
        "direction": direction,
        "forecast_range_usd_cwt": [round(lower, 2), round(upper, 2)],
        "model_mae_usd_cwt": round(bundle["model_mae"], 2),
        "naive_mae_usd_cwt": round(bundle["naive_mae"], 2),
        "beats_naive": bool(bundle["model_mae"] < bundle["naive_mae"]),
        "model_updated_at": bundle["trained_at"],
    }

    latest.to_csv(FEATURES_PATH)
    return forecast
