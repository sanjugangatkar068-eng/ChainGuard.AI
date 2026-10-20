"""The ChainGuard orchestrator agent.

This is the agent that *maintains the roles*. It:

1. invokes every role agent in the correct order, passing each one the outputs it
   depends on, and records a trace of what ran;
2. tolerates a failing role — one broken agent is recorded and skipped over rather
   than failing the whole request;
3. in **autonomous mode**, reacts to incoming signals with no human trigger: it
   ingests feeds, raises a disruption for each supply-chain-relevant headline, runs
   the full pipeline, and raises a notification when the result escalates.

Nothing here executes a supply-chain action — the orchestrator acts on its own, but
its output is always a recommendation plus a notification.
"""

import json
import os
import time

import alerting
import database as db
from agents import (
    compliance_agent,
    disruption_sensing,
    escalation_agent,
    explanation_agent,
    inventory_agent,
    logistics_agent,
    scenario_planning,
    signal_ingestion_agent,
    supplier_risk_agent,
)
from models import DisruptionRequest, ScenarioRequest
from signals import fetch_signals

DEFAULT_DISRUPTION = {
    "severity": "medium",
    "delay_days": 0,
    "disruption_type": "other",
    "location": "Unknown",
    "title": "Manual scenario",
}

# How an incoming headline's disruption type maps to an assumed severity and delay.
SEVERITY_BY_TYPE = {
    "port_closure": "high",
    "weather": "high",
    "supplier_outage": "high",
    "tariff_change": "medium",
    "port_congestion": "medium",
    "demand_spike": "medium",
    "other": "low",
}

DELAY_BY_TYPE = {
    "port_closure": 14,
    "weather": 7,
    "supplier_outage": 10,
    "tariff_change": 5,
    "port_congestion": 6,
    "demand_spike": 3,
    "other": 3,
}

ROLES = [
    {"key": "disruption_sensing", "name": "Disruption Sensing Agent",
     "role": "Ingest signals, classify the event and score risk."},
    {"key": "scenario_planning", "name": "Scenario Planning Agent",
     "role": "Compare wait / reroute / expedite options on cost, delay and risk."},
    {"key": "logistics", "name": "Rerouting & Logistics Agent",
     "role": "Turn the chosen scenario into a route and revised ETA."},
    {"key": "inventory", "name": "Inventory Rebalancing Agent",
     "role": "Recompute reorder point and replenishment needs."},
    {"key": "supplier_risk", "name": "Supplier Risk Agent",
     "role": "Score supplier exposure and flag concentration (when suppliers are given)."},
    {"key": "compliance_audit", "name": "Compliance & Audit Agent",
     "role": "Flag high-risk cases and budget breaches; produce a report."},
    {"key": "escalation", "name": "Escalation Agent",
     "role": "Decide whether to alert a human at the configured threshold."},
    {"key": "explanation", "name": "Explanation Agent",
     "role": "Narrate the assessment (LLM if configured, else rules)."},
]


def interval_seconds() -> int:
    try:
        return max(0, int(os.getenv("ORCHESTRATOR_INTERVAL_SECONDS", "0") or 0))
    except ValueError:
        return 0


def describe() -> dict:
    """Describe the orchestrator and the roles it maintains."""
    interval = interval_seconds()
    return {
        "orchestrator": "ChainGuard Orchestrator",
        "mode": "autonomous" if interval > 0 else "on-demand",
        "interval_seconds": interval,
        "alert_threshold": alerting.min_level(),
        "autonomous_endpoint": "POST /api/orchestrator/cycle",
        "roles": ROLES,
    }


def run_pipeline(disruption, params):
    """Run every role in order, recording a trace. One failure never stops the rest."""
    result = {}
    trace = []
    started = time.perf_counter()

    def role(name, fn, deps=()):
        for dep in deps:
            # Treat a present-but-false value (e.g. human_approval_required=False)
            # as available; only a missing or None dependency blocks a role.
            if dep not in result or result[dep] is None:
                trace.append({
                    "agent": name,
                    "status": "skipped",
                    "reason": f"dependency '{dep}' unavailable",
                })
                return None

        step_started = time.perf_counter()
        try:
            value = fn()
        except Exception as exc:  # noqa: BLE001 - one role must not break the pipeline
            trace.append({
                "agent": name,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}"[:200],
            })
            return None

        trace.append({
            "agent": name,
            "status": "ok",
            "ms": round((time.perf_counter() - step_started) * 1000, 2),
        })
        result[name] = value
        return value

    sensing = role("disruption_sensing",
                   lambda: disruption_sensing(disruption or DEFAULT_DISRUPTION))
    planning = role("scenario_planning",
                    lambda: scenario_planning(disruption, params),
                    deps=("disruption_sensing",))
    role("logistics", lambda: logistics_agent(planning), deps=("scenario_planning",))
    role("inventory", lambda: inventory_agent(disruption, params))
    if getattr(params, "suppliers", None):
        role("supplier_risk", lambda: supplier_risk_agent(params.suppliers, disruption))

    compliance = role(
        "compliance_audit",
        lambda: compliance_agent(sensing, planning, result.get("logistics")),
        deps=("disruption_sensing", "scenario_planning", "logistics"),
    )

    result["human_approval_required"] = bool(
        compliance and compliance.get("review_required")
    )

    role("escalation",
         lambda: escalation_agent(sensing, compliance),
         deps=("disruption_sensing", "compliance_audit"))
    role("explanation",
         lambda: explanation_agent(result),
         deps=("disruption_sensing", "scenario_planning", "logistics",
               "inventory", "human_approval_required"))

    result["pipeline"] = {
        "orchestrator": "ChainGuard Orchestrator",
        "trace": trace,
        "agents_ok": sum(1 for step in trace if step["status"] == "ok"),
        "agents_failed": sum(1 for step in trace if step["status"] == "error"),
        "agents_skipped": sum(1 for step in trace if step["status"] == "skipped"),
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
    }
    return result


def _known_titles(limit=200):
    titles = set()
    for row in db.list_records("disruptions", limit):
        try:
            title = json.loads(row["payload"]).get("title", "")
        except (ValueError, TypeError):
            continue
        if title:
            titles.add(title.strip().lower())
    return titles


def run_autonomous_cycle(limit=5):
    """Scan signals, act on the relevant ones, and notify — with no human trigger."""
    ingested = signal_ingestion_agent(fetch_signals(limit=limit))
    relevant = [s for s in ingested["signals"] if s["disruption_type"] != "other"]
    known = _known_titles()

    items = []
    escalated = notified = 0

    for signal in relevant:
        title = (signal.get("title") or "").strip()[:160]
        if len(title) < 3 or title.lower() in known:
            continue
        known.add(title.lower())

        payload = DisruptionRequest(
            title=title,
            disruption_type=signal["disruption_type"],
            location="Unknown",
            severity=SEVERITY_BY_TYPE.get(signal["disruption_type"], "medium"),
            description=(signal.get("summary") or "")[:500],
            delay_days=DELAY_BY_TYPE.get(signal["disruption_type"], 5),
        ).model_dump()

        disruption_id = db.add_record(
            "disruptions", "created_at, payload",
            (db.now(), json.dumps(payload)),
        )
        db.log_event("autonomous_disruption_created", "orchestrator", {
            "disruption_id": disruption_id,
            "signal_source": signal.get("source"),
        })

        result = run_pipeline(
            {"id": disruption_id, **payload},
            ScenarioRequest(disruption_id=disruption_id),
        )

        analysis_id = db.add_record(
            "analyses", "created_at, disruption_id, payload, status",
            (db.now(), disruption_id, json.dumps(result), "pending"),
        )

        approval_id = None
        if result["human_approval_required"]:
            approval_id = db.add_record(
                "approvals", "created_at, analysis_id, status",
                (db.now(), analysis_id, "pending"),
            )
            escalated += 1

        alert_id = None
        if result.get("escalation", {}).get("escalate"):
            level = result["disruption_sensing"]["risk_level"]
            alert_id = alerting.dispatch(
                subject=f"{level} disruption (autonomous)",
                message=result.get("explanation", {}).get("explanation", ""),
                level=level,
                context={
                    "disruption_id": disruption_id,
                    "analysis_id": analysis_id,
                    "approval_id": approval_id,
                    "source": signal.get("source"),
                },
            )
            notified += 1

        items.append({
            "disruption_id": disruption_id,
            "analysis_id": analysis_id,
            "approval_id": approval_id,
            "alert_id": alert_id,
            "title": title,
            "risk_level": result["disruption_sensing"]["risk_level"],
        })

    summary = {
        "scanned": ingested["count"],
        "relevant": len(relevant),
        "created": len(items),
        "escalated": escalated,
        "notified": notified,
        "data_source": ingested["data_source"],
        "items": items,
    }

    db.log_event("autonomous_cycle", "orchestrator", {
        "scanned": summary["scanned"],
        "relevant": summary["relevant"],
        "created": summary["created"],
        "notified": summary["notified"],
    })
    return summary
