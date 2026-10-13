from datetime import datetime

from .config import SENDER_NAME


def euro_litre_equivalent(usd_cwt: float, eurusd: float) -> float:
    """Convert USD/cwt to a rough EUR/litre global-market equivalent.

    1 cwt = 45.359237 kg.
    1 kg of milk is approximately 1 litre for this rough indicator.
    """
    usd_per_kg = usd_cwt / 45.359237
    return usd_per_kg / eurusd


def usd_to_eur_cwt(usd_cwt: float, eurusd: float) -> float:
    """Convert USD/cwt to EUR/cwt."""
    return usd_cwt / eurusd


def build_subject(forecast: dict) -> str:
    generated = datetime.fromisoformat(forecast["generated_at"].replace("Z", "+00:00"))
    date_label = generated.strftime("%d %b")
    return f"Milk Price Outlook \u2014 Monday {date_label}"


def build_html(forecast: dict, commentary: dict, eurusd: float) -> str:
    direction = forecast["direction"]
    change = forecast["forecast_change_pct"]

    if direction == "up":
        arrow = "&#9650;"
        direction_text = f"up {abs(change):.1f}%"
        colour = "#166534"
    elif direction == "down":
        arrow = "&#9660;"
        direction_text = f"down {abs(change):.1f}%"
        colour = "#991b1b"
    else:
        arrow = "&#9644;"
        direction_text = "broadly stable"
        colour = "#374151"

    last_eur = usd_to_eur_cwt(forecast["last_price_usd_cwt"], eurusd)
    forecast_eur = usd_to_eur_cwt(forecast["forecast_price_usd_cwt"], eurusd)
    lower, upper = forecast["forecast_range_usd_cwt"]
    lower_eur = usd_to_eur_cwt(lower, eurusd)
    upper_eur = usd_to_eur_cwt(upper, eurusd)
    euro_litre = euro_litre_equivalent(forecast["forecast_price_usd_cwt"], eurusd)

    why_items = "".join(
        f'<li style="margin-bottom:8px;">{item}</li>' for item in commentary["why"]
    )
    watch_items = "".join(
        f'<li style="margin-bottom:8px;">{item}</li>' for item in commentary["watch"]
    )

    updated = datetime.fromisoformat(
        forecast["model_updated_at"].replace("Z", "+00:00")
    ).strftime("%d %b %Y")

    return f"""<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;color:#111827;">
    <div style="max-width:600px;margin:0 auto;padding:16px;">
      <div style="background:#ffffff;border-radius:14px;padding:22px;border:1px solid #e5e7eb;">

        <p style="margin:0 0 16px;font-size:16px;">Hi Farmer,</p>

        <p style="margin:0 0 6px;font-size:16px;">
          Last week's benchmark price:<br>
          <strong style="font-size:22px;">\u20ac{last_eur:.2f} per cwt</strong>
          <span style="font-size:14px;color:#6b7280;">(${forecast['last_price_usd_cwt']:.2f})</span>
        </p>

        <p style="margin:0 0 18px;font-size:16px;">
          Next week's estimate:<br>
          <strong style="font-size:26px;color:{colour};">
            \u20ac{forecast_eur:.2f} per cwt {arrow}
          </strong>
          <span style="font-size:14px;color:#6b7280;">(${forecast['forecast_price_usd_cwt']:.2f})</span><br>
          <span style="color:{colour};font-weight:600;">{direction_text}</span>
        </p>

        <p style="margin:0 0 18px;font-size:15px;color:#374151;">
          Likely range: <strong>\u20ac{lower_eur:.2f}\u2013\u20ac{upper_eur:.2f} per cwt</strong><br>
          In euro terms: <strong>about \u20ac{euro_litre:.2f} per litre equivalent</strong><br>
          <span style="font-size:13px;color:#6b7280;">Global benchmark \u2014 not your co-op milk price.</span>
        </p>

        <h2 style="font-size:17px;margin:0 0 8px;">What's moving it</h2>
        <ul style="padding-left:20px;margin:0 0 18px;font-size:15px;line-height:1.45;">
          {why_items}
        </ul>

        <h2 style="font-size:17px;margin:0 0 8px;">What to watch</h2>
        <ul style="padding-left:20px;margin:0 0 18px;font-size:15px;line-height:1.45;">
          {watch_items}
        </ul>

        <p style="margin:0 0 14px;font-size:15px;line-height:1.45;">
          {commentary['plain_english_summary']}
        </p>

        <p style="margin:0;font-size:13px;color:#6b7280;">
          This is an estimate based on recent trends, not a guarantee.<br>
          Model last updated: {updated}.<br>
          Sent by {SENDER_NAME}.
        </p>

      </div>
    </div>
  </body>
</html>"""
