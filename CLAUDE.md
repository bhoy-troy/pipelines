# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Automated weekly dairy market outlook for Irish farmers. Downloads market data (Yahoo Finance, Open-Meteo weather, World Bank fertiliser prices, GlobalDairyTrade auction results), trains a Ridge regression model to predict next week's CME Class III milk price, generates plain-English commentary via Gemini (Groq fallback), and emails the outlook to subscribers via Brevo.

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Train model only (downloads 2 years of data, saves to models/)
python -m src.run_weekly --train-only

# Send test email (first recipient only)
python -m src.run_weekly --test-email

# Full weekly run (train + forecast + email all recipients)
python -m src.run_weekly
```

No test suite exists. No linter/formatter is configured.

## Architecture

The pipeline runs as a single sequential flow orchestrated by `src/run_weekly.py`:

1. **Data collection** (`data_sources.py`) - Yahoo Finance (milk futures, oil, corn, soybeans, wheat, FX), Open-Meteo weather anomalies for 4 dairy regions, World Bank fertiliser prices, GDT auction scraping
2. **Feature engineering** (`features.py`) - Lag features, weekly/monthly changes, rolling stats, calendar seasonality, weather anomalies. `FEATURE_COLUMNS` list defines the model input schema
3. **Model** (`model.py`) - StandardScaler + Ridge regression pipeline. 80/20 time-series split. Compares against naive baseline (last week's price). Saves model bundle via joblib to `models/class3_model.joblib`
4. **LLM commentary** (`llm_commentary.py`) - Calls Gemini API (or Groq fallback) with structured JSON prompt (`PROMPT.MD`). Falls back to a hardcoded safe summary if both LLMs fail. Groq path is currently commented out
5. **Email** (`email_builder.py`, `email_sender.py`) - Builds inline-styled HTML email, sends via Brevo SMTP API

`config.py` centralises all env vars, file paths, API URLs, ticker symbols, and weather locations. **Bug:** `model.py` imports `FEATURE_COLUMNS` from `config.py` but it's only defined in `features.py` - this import will fail at runtime.

## Environment Variables

Required in `.env` or as GitHub Actions secrets: `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME`, `RECIPIENTS` (format: `Name,email;Name,email`), `GEMINI_API_KEY`. Optional: `GROQ_API_KEY`.

## GitHub Actions

- `weekly.yml` - Main pipeline. Runs Monday 06:30 UTC. Python 3.12. Uploads `output/` and `models/` as artifacts.
- `2.yml` - CDN dependency checker (copied from another project, references `fedora-eln/content-resolver`). Not related to the dairy pipeline.
