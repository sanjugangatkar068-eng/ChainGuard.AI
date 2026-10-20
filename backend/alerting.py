"""Best-effort escalation and alerting.

Alerts are always recorded in the database. Delivery is attempted only when a
webhook URL is configured (ALERT_WEBHOOK_URL); otherwise the alert is recorded
with channel "log". Delivery failures never break the request pipeline.

Configuration (all optional):

    ALERT_MIN_LEVEL    low | medium | high | critical   (default: high)
    ALERT_WEBHOOK_URL  HTTP endpoint to POST the alert to
"""

import json
import os

import httpx

import database as db

LEVEL_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
DEFAULT_TIMEOUT = 6.0


def min_level() -> str:
    value = (os.getenv("ALERT_MIN_LEVEL", "high") or "high").strip().lower()
    return value if value in LEVEL_ORDER else "high"


def webhook_url() -> str:
    return (os.getenv("ALERT_WEBHOOK_URL", "") or "").strip()


def should_alert(risk_level: str) -> bool:
    return LEVEL_ORDER.get(risk_level, 0) >= LEVEL_ORDER[min_level()]


def dispatch(subject, message, level, context=None, timeout=DEFAULT_TIMEOUT) -> int:
    """Record an alert and best-effort deliver it. Returns the alert id."""
    url = webhook_url()
    channel = "webhook" if url else "log"
    payload = {
        "subject": subject,
        "message": message,
        "level": level,
        "context": context or {},
    }

    delivered = False
    if url:
        try:
            response = httpx.post(url, json=payload, timeout=timeout)
            delivered = response.status_code < 400
        except httpx.HTTPError:
            delivered = False

    alert_id = db.add_record(
        "alerts",
        "created_at, level, subject, message, channel, delivered, "
        "acknowledged, details",
        (
            db.now(), level, subject, message, channel,
            int(delivered), 0, json.dumps(payload),
        ),
    )

    db.log_event(
        "alert_dispatched",
        "system",
        {"alert_id": alert_id, "channel": channel, "delivered": delivered},
    )
    return alert_id
