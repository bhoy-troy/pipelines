# Irish Dairy Farmer Weekly Milk Price Outlook

A free, automated Monday-morning email that gives dairy farmers:

- Last week's CME Class III milk benchmark
- Next week's estimated benchmark and likely direction
- Three plain-English reasons
- One thing to watch
- A rough euro-market equivalent

It uses **Brevo** for email delivery. Brevo's free plan provides 300 emails/day, with no credit card required.

## Important

CME Class III Milk Futures are a **US/global dairy benchmark**, not the Irish co-op farm-gate milk price.  
The email explicitly labels the euro figure as a rough global-market equivalent.

## Free services used

| Service | Purpose | Free tier |
|---|---|---|
| Yahoo Finance | CME Class III, oil, corn, soybeans, wheat, FX | Free market data |
| Open-Meteo | Weather in key dairy regions | Free, no API key |
| World Bank Pink Sheet | Monthly fertiliser prices | Free download |
| GlobalDairyTrade | Latest public auction result | Free public page |
| Gemini API | Short farmer-friendly commentary | Free tier |
| Groq API | Optional fallback commentary | Free tier |
| Brevo | Transactional email delivery | 300 emails/day free |
| GitHub Actions | Weekly scheduling | Free for public repos |

## Project structure

```text
dairy-price-outlook/
├── src/
│   ├── config.py
│   ├── data_sources.py
│   ├── features.py
│   ├── model.py
│   ├── llm_commentary.py
│   ├── email_builder.py
│   ├── email_sender.py
│   └── run_weekly.py
├── models/
├── output/
├── .github/workflows/weekly.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create free accounts

1. Create a Brevo account.
2. Verify your sender email address in Brevo.
3. Go to **SMTP & API > API Keys** and create an API key.
4. Create a Google AI Studio API key for Gemini.
5. Optionally create a Groq API key as a fallback.

### 3. Configure environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit:

```env
BREVO_API_KEY=your_brevo_api_key
BREVO_SENDER_EMAIL=you@example.com
BREVO_SENDER_NAME=Milk Price Outlook
RECIPIENTS=Farmer One,farmer1@example.com;Farmer Two,farmer2@example.com
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=optional_groq_key
```

Recipient format:

```text
Name,email;Name,email
```

### 4. Train the model

```bash
python -m src.run_weekly --train-only
```

This downloads two years of data, builds features, trains the model, saves it to `models/`, and writes a backtest report to `output/backtest_report.json`.

### 5. Send a test email

```bash
python -m src.run_weekly --test-email
```

### 6. Run the full weekly job

```bash
python -m src.run_weekly
```

## GitHub Actions

Put this project in a **private GitHub repository** if it contains recipient email addresses.

Add these repository secrets:

```text
BREVO_API_KEY
BREVO_SENDER_EMAIL
BREVO_SENDER_NAME
RECIPIENTS
GEMINI_API_KEY
GROQ_API_KEY
```

The workflow runs every Monday. GitHub Actions cron uses UTC, so the schedule is set to 06:30 UTC. That is approximately 07:30 Irish time in summer and 06:30 Irish time in winter. Adjust if exact local timing matters.

## Model approach

The first version uses a regularised linear model with:

- Latest CME Class III price
- One-, two-, four- and eight-week lags
- Weekly changes in oil, corn, soybeans, wheat, EUR/USD and NZD/USD
- Rolling volatility and trend
- Calendar seasonality
- Latest GDT change
- Monthly fertiliser year-on-year change
- Weather anomalies for Munster, Northern Ireland, Netherlands and Waikato

It predicts next week's CME Class III close.

The model also calculates a naive baseline. If the trained model does not beat the naive baseline in backtesting, the email defaults to a cautious **"broadly stable"** message.

## Running locally

```bash
python -m src.run_weekly --train-only
python -m src.run_weekly --test-email
python -m src.run_weekly
```

## Files produced

- `models/class3_model.joblib`
- `output/latest_features.csv`
- `output/forecast.json`
- `output/backtest_report.json`
- `output/email_preview.html`
