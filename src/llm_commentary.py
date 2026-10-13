import json
import re
import time

import requests

from .config import DEEPSEEK_API_KEY, GEMINI_API_KEY, GEMINI_MODEL, GROQ_API_KEY

SYSTEM_PROMPT = """You are an experienced Irish farm advisor writing a short Monday dairy-market update.

Your reader is an Irish dairy farmer. Write in plain English. All prices should be discussed in euro terms. Avoid financial jargon, technical model language, and speculation.

Use ONLY the facts supplied in DATA. Do not invent prices, percentages, weather events, auction results, policy changes, or causes.

The DATA includes weekly percentage changes for: butter, cheese, natural gas (energy costs), feed inputs (corn, soybeans, wheat), the milk-to-feed ratio (farm profitability signal), currency movements, and weather in key dairy regions. Use whichever are most relevant to explain the price direction.

Rules:
- Maximum 150 words in total.
- Write exactly three short bullet points under "why".
- Write exactly one short bullet point under "watch".
- If the data says a market input did not change much, say it was broadly stable.
- Do not claim certainty. Use words such as "suggests", "supports", "may", or "points to".
- Do not mention CME, futures, regression, features, AI, or model internals.
- Do not use tables.
- Return valid JSON only. No markdown, no explanation outside JSON.

Return this exact JSON structure:
{
  "direction": "up|down|stable",
  "why": ["short reason 1", "short reason 2", "short reason 3"],
  "watch": ["one short risk or opportunity"],
  "plain_english_summary": "one clear sentence"
}
"""


USER_PROMPT_TEMPLATE = """DATA:
{data}

Write the Monday dairy-market update now."""


def _clean_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("LLM did not return JSON")

    parsed = json.loads(text[start : end + 1])

    required = {"direction", "why", "watch", "plain_english_summary"}
    if not required.issubset(parsed):
        raise ValueError("LLM JSON is missing required fields")

    if parsed["direction"] not in {"up", "down", "stable"}:
        raise ValueError("Invalid direction")

    if not isinstance(parsed["why"], list) or len(parsed["why"]) != 3:
        raise ValueError("LLM must return exactly three reasons")

    if not isinstance(parsed["watch"], list) or len(parsed["watch"]) != 1:
        raise ValueError("LLM must return exactly one watch item")

    return parsed


def _gemini_commentary(data: dict) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {
                "role": "user",
                "parts": [{"text": USER_PROMPT_TEMPLATE.format(data=json.dumps(data, indent=2))}],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 700,
            "responseMimeType": "application/json",
        },
    }

    response = requests.post(url, json=payload, timeout=45)
    response.raise_for_status()

    candidates = response.json().get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned no candidates")

    text = candidates[0]["content"]["parts"][0]["text"]
    return _clean_json(text)


def _openai_compatible_commentary(data: dict, url: str, api_key: str, model: str) -> dict:
    """Call any OpenAI-compatible chat completions API (Grok, HuggingFace, etc.)."""
    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(data=json.dumps(data, indent=2)),
            },
        ],
    }

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=45,
    )
    response.raise_for_status()

    text = response.json()["choices"][0]["message"]["content"]
    return _clean_json(text)


def generate_commentary(facts: dict) -> dict:
    """Generate commentary using Gemini, falling back to Groq, then DeepSeek, then a safe local version."""
    errors = []

    # 1. Gemini (2 retries, 5s backoff)
    if GEMINI_API_KEY:
        for attempt in range(2):
            try:
                return _gemini_commentary(facts)
            except Exception as exc:
                errors.append(f"Gemini attempt {attempt + 1}: {exc}")
                if attempt < 1:
                    time.sleep(5)

    # 2. Groq fallback
    if GROQ_API_KEY:
        try:
            return _openai_compatible_commentary(
                facts,
                url="https://api.groq.com/openai/v1/chat/completions",
                api_key=GROQ_API_KEY,
                model="qwen/qwen3.8-27b",
            )
        except Exception as exc:
            errors.append(f"Groq: {exc}")

    # 3. DeepSeek fallback
    if DEEPSEEK_API_KEY:
        try:
            return _openai_compatible_commentary(
                facts,
                url="https://api.deepseek.com/chat/completions",
                api_key=DEEPSEEK_API_KEY,
                model="deepseek-chat",
            )
        except Exception as exc:
            errors.append(f"DeepSeek: {exc}")

    # 4. Local safe fallback
    direction = facts.get("direction", "stable")
    change = facts.get("forecast_change_pct", 0)

    if direction == "up":
        summary = "The global milk benchmark is estimated to move slightly higher next week."
    elif direction == "down":
        summary = "The global milk benchmark is estimated to move slightly lower next week."
    else:
        summary = "The global milk benchmark is expected to remain broadly stable next week."

    return {
        "direction": direction,
        "why": [
            f"The benchmark is estimated to change by {change:+.1f}% next week.",
            "Feed, energy and currency movements are included in the weekly outlook.",
            "The latest global dairy auction signal is included where available.",
        ],
        "watch": ["Watch feed costs and currency movements, as both can affect farm margins."],
        "plain_english_summary": summary,
        "fallback_used": True,
        "llm_errors": errors,
    }
