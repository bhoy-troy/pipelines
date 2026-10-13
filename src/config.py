import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_NAME = os.getenv("SENDER_NAME", "Milk Price Outlook")
RECIPIENTS_RAW = os.getenv("RECIPIENTS", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

MODEL_DIR = BASE_DIR / "models"
OUTPUT_DIR = BASE_DIR / "output"
MODEL_PATH = MODEL_DIR / "class3_model.joblib"
FEATURES_PATH = OUTPUT_DIR / "latest_features.csv"
FORECAST_PATH = OUTPUT_DIR / "forecast.json"
BACKTEST_PATH = OUTPUT_DIR / "backtest_report.json"
EMAIL_PREVIEW_PATH = OUTPUT_DIR / "email_preview.html"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

YAHOO_TICKERS = {
    "milk": "DC=F",
    "oil": "CL=F",
    "corn": "ZC=F",
    "soybeans": "ZS=F",
    "wheat": "ZW=F",
    "butter": "CB=F",
    "cheese": "CSC=F",
    "natgas": "NG=F",
    "eurusd": "EURUSD=X",
    "nzdusd": "NZDUSD=X",
}

# Open-Meteo locations: name, latitude, longitude
WEATHER_LOCATIONS = [
    ("Munster", 52.25, -8.5),
    ("Northern Ireland", 54.6, -6.5),
    ("Netherlands", 52.1, 5.3),
    ("Waikato NZ", -37.7, 175.2),
]

WORLD_BANK_PINK_SHEET_URL = (
    "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx"
)

GDT_RESULTS_URL = "https://www.globaldairytrade.info/en/product-results"

# GEMINI_MODEL = "gemini-flash-latest"
GEMINI_MODEL = "gemini-3.8-flash"

def parse_recipients(raw: str):
    recipients = []

    for item in raw.split(";"):
        item = item.strip()
        if not item:
            continue
        if "," not in item:
            name = ''
            email  = item
        else:
            name, email = item.rsplit(",", 1)
        recipients.append({"name": name.strip(), "email": email.strip()})
    return recipients
