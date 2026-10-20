import json
from math import ceil

from alerting import min_level, should_alert
from llm import LLMUnavailable, complete, is_configured

# Keyword heuristics used to classify an incoming headline without an LLM.
KEYWORD_MAP = {
    "port_closure": ["closure", "closed", "blockade", "blocked", "canal", "strait",
                     "shut", "strike", "attack", "reroute", "diversion", "suez",
                     "hormuz", "red sea", "cape of good hope"],
    "port_congestion": ["congestion", "backlog", "queue", "queues", "delays at",
                        "vessel", "freight", "shipping"],
    "weather": ["storm", "hurricane", "typhoon", "flood", "drought", "cyclone",
                "weather", "earthquake"],
    "tariff_change": ["tariff", "duty", "duties", "levy", "trade war", "sanction",
                      "sanctions"],
    "supplier_outage": ["supplier", "factory", "plant", "shortage", "bankrupt",
                        "outage", "fire"],
    "demand_spike": ["surge", "spike", "demand", "stockout"],
}

# Illustrative response routes per recommended action.
ROUTE_BY_ACTION = {
    "wait": "Existing route (monitor)",
    "reroute": "Alternate corridor diversion",
    "expedite": "Air freight / alternate supplier lane",
}


def _risk_level(score):
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def classify_signal(text):
    """Map free text to a disruption_type using keyword heuristics."""
    haystack = (text or "").lower()
    for disruption_type, words in KEYWORD_MAP.items():
        if any(word in haystack for word in words):
            return disruption_type
    return "other"


def signal_ingestion_agent(signals):
    """Turn raw feed items into classified signals."""
    items = []
    for signal in signals:
        text = f"{signal.get('title', '')} {signal.get('summary', '')}"
        items.append({
            "title": signal.get("title", ""),
            "link": signal.get("link", ""),
            "published": signal.get("published"),
            "source": signal.get("source", "unknown"),
            "disruption_type": classify_signal(text),
        })

    live = [i for i in items if i["source"] != "sample"]
    return {
        "agent": "Disruption Sensing Agent (signal ingestion)",
        "count": len(items),
        "signals": items,
        "data_source": "Live RSS/Atom feeds" if live else "Offline sample",
    }


def disruption_sensing(disruption):
    severity_scores = {
        "low": 20,
        "medium": 45,
        "high": 75,
        "critical": 95
    }

    severity = disruption.get("severity", "medium")
    delay_days = disruption.get("delay_days", 0)

    score = severity_scores.get(severity, 45)
    score = min(100, score + delay_days)

    # Confidence rises as more of the record is populated.
    confidence = 0.6
    if delay_days > 0:
        confidence += 0.2
    if disruption.get("estimated_loss_usd", 0):
        confidence += 0.2
    confidence = round(min(1.0, confidence), 2)

    return {
        "agent": "Disruption Sensing Agent",
        "risk_score": score,
        "risk_level": _risk_level(score),
        "confidence": confidence,
        "disruption_type": disruption.get("disruption_type", "other"),
        "location": disruption.get("location", "Unknown"),
        "source": "user-provided demo data",
        "signals": [
            disruption.get("title", "Manual scenario"),
            f"Delay: {delay_days} days",
            f"Severity: {severity}"
        ],
        "data_source": "User-provided demo data"
    }


def scenario_planning(disruption, params):
    delay = disruption.get("delay_days", 0) if disruption else 0
    tariff = disruption.get("tariff_percent", 0) if disruption else 0
    loss = disruption.get("estimated_loss_usd", 0) if disruption else 0

    base_cost = (
        loss
        + params.unit_cost_usd
        * params.demand_units_per_day
        * delay
        * tariff / 100
    )

    scenarios = [
        {
            "id": "wait",
            "name": "Wait and monitor",
            "extra_cost_usd": round(base_cost, 2),
            "delay_days": delay,
            "risk": "high" if delay >= 7 else "medium"
        },
        {
            "id": "reroute",
            "name": "Reroute shipment",
            "extra_cost_usd": round(
                base_cost + params.reroute_cost_usd, 2
            ),
            "delay_days": ceil(delay * 0.35),
            "risk": "medium"
        },
        {
            "id": "expedite",
            "name": "Expedite or alternate supplier",
            "extra_cost_usd": round(
                base_cost + params.expedite_cost_usd, 2
            ),
            "delay_days": ceil(delay * 0.2),
            "risk": "medium"
        }
    ]

    for scenario in scenarios:
        scenario["within_budget"] = (
            scenario["extra_cost_usd"] <= params.max_budget_usd
        )

    eligible = [
        scenario for scenario in scenarios
        if scenario["within_budget"]
    ]

    candidates = eligible if eligible else scenarios

    best = min(
        candidates,
        key=lambda item: (
            item["delay_days"],
            item["extra_cost_usd"]
        )
    )

    return {
        "agent": "Scenario Planning Agent",
        "scenarios": scenarios,
        "recommended_scenario": best,
        "assumptions": [
            "Costs and delay reductions are estimates.",
            "Carrier capacity and supplier availability require verification."
        ]
    }


def logistics_agent(scenario_result):
    selected = scenario_result["recommended_scenario"]

    return {
        "agent": "Rerouting & Logistics Agent",
        "recommended_action": selected["id"],
        "recommended_route": ROUTE_BY_ACTION.get(selected["id"], "Existing route"),
        "estimated_cost_usd": selected["extra_cost_usd"],
        "estimated_delay_days": selected["delay_days"],
        "revised_eta_days": selected["delay_days"],
        "execution_status": "recommendation_only",
        "next_steps": [
            "Verify route and carrier availability",
            "Confirm revised delivery date",
            "Obtain approval before changing bookings"
        ]
    }


def inventory_agent(disruption, params):
    delay = disruption.get("delay_days", 0) if disruption else 0

    demand_during_lead_time = (
        params.demand_units_per_day * params.lead_time_days
    )

    reorder_point = (
        demand_during_lead_time + params.safety_stock
    )

    projected_inventory = max(
        0,
        params.current_inventory
        - params.demand_units_per_day * delay
    )

    replenishment = max(
        0, reorder_point - projected_inventory
    )

    return {
        "agent": "Inventory Rebalancing Agent",
        "current_inventory": params.current_inventory,
        "reorder_point": reorder_point,
        "projected_inventory": projected_inventory,
        "recommended_replenishment_units": replenishment,
        "estimated_replenishment_cost_usd": round(
            replenishment * params.unit_cost_usd, 2
        )
    }


def supplier_risk_agent(suppliers, disruption=None):
    """Score suppliers for exposure and flag sourcing concentration."""
    total_spend = sum(s.spend_usd for s in suppliers) or 1.0
    location = (disruption or {}).get("location", "") or ""

    items = []
    for supplier in suppliers:
        score = 0
        if supplier.single_source:
            score += 40
        score += min(20, supplier.lead_time_days)
        score += (supplier.tier - 1) * 5
        if location and supplier.country.lower() == location.lower():
            score += 20
        score = min(100, score)

        items.append({
            "name": supplier.name,
            "tier": supplier.tier,
            "country": supplier.country,
            "single_source": supplier.single_source,
            "spend_share_pct": round(100 * supplier.spend_usd / total_spend, 1),
            "risk_score": score,
            "risk_level": _risk_level(score),
        })

    items.sort(key=lambda i: i["risk_score"], reverse=True)

    top = max(items, key=lambda i: i["spend_share_pct"]) if items else None
    concentration_risk = bool(top and top["spend_share_pct"] >= 40)

    return {
        "agent": "Supplier Risk Agent",
        "suppliers": items,
        "concentration_risk": concentration_risk,
        "top_supplier": top["name"] if top else None,
        "highest_risk_supplier": items[0]["name"] if items else None,
        "recommendation": (
            "Diversify sourcing away from the dominant supplier."
            if concentration_risk
            else "Spend is reasonably distributed across suppliers."
        ),
    }


def compliance_agent(sensing, scenarios, logistics):
    flags = []

    if sensing["risk_level"] in ["high", "critical"]:
        flags.append("High-risk disruption requires human review.")

    if logistics["recommended_action"] == "expedite":
        flags.append(
            "Verify alternate supplier qualification and contracts."
        )

    if not any(
        s["within_budget"] for s in scenarios["scenarios"]
    ):
        flags.append("All scenarios exceed the configured budget.")

    review_required = bool(flags)

    return {
        "agent": "Compliance & Audit Agent",
        "review_required": review_required,
        "flags": flags,
        "decision_logged": True,
        "report": {
            "risk_level": sensing["risk_level"],
            "policy": "recommendation-only; no autonomous external action",
            "review_required": review_required,
            "outcome": "pending human approval" if review_required else "auto-cleared",
        },
    }


def escalation_agent(sensing, compliance):
    """Decide whether this assessment should be escalated to a human."""
    level = sensing["risk_level"]
    escalate = compliance["review_required"] and should_alert(level)

    return {
        "agent": "Escalation Agent",
        "escalate": escalate,
        "risk_level": level,
        "threshold": min_level(),
        "reason": (
            "Risk at or above the alert threshold and review is required."
            if escalate
            else "Below the alert threshold or no review required."
        ),
    }


EXPLANATION_SYSTEM = (
    "You are ChainGuard AI, a supply-chain resilience analyst. "
    "Given a JSON risk assessment, write a concise three-sentence rationale a "
    "logistics manager can act on. Cite the specific numbers, state the "
    "recommended action, and note whether human approval is required. "
    "Do not invent data that is not in the JSON."
)


def _rule_based_explanation(result):
    sensing = result["disruption_sensing"]
    planning = result["scenario_planning"]
    inventory = result["inventory"]
    recommended = planning["recommended_scenario"]

    closing = (
        "Human approval is required before acting."
        if result["human_approval_required"]
        else "No approval is required."
    )

    return (
        f"Detected a {sensing['risk_level']}-risk "
        f"{sensing['disruption_type']} at {sensing['location']} "
        f"(score {sensing['risk_score']}/100, confidence {sensing['confidence']}). "
        f"The scenario planner recommends '{recommended['name']}' at about "
        f"${recommended['extra_cost_usd']:,.0f} extra cost and "
        f"{recommended['delay_days']} days' delay, with "
        f"{inventory['recommended_replenishment_units']} units of inventory "
        f"replenishment. {closing}"
    )


def explanation_agent(result):
    """Narrate the assessment, using the LLM when available."""
    if is_configured():
        try:
            text = complete(
                EXPLANATION_SYSTEM,
                json.dumps(result, indent=2),
                max_tokens=320,
            )
            return {
                "agent": "Explanation Agent",
                "reasoning_source": "llm",
                "explanation": text,
            }
        except LLMUnavailable:
            pass

    return {
        "agent": "Explanation Agent",
        "reasoning_source": "rules",
        "explanation": _rule_based_explanation(result),
    }


def run_supply_chain_agents(disruption, params):
    sensing = disruption_sensing(
        disruption or {
            "severity": "medium",
            "delay_days": 0,
            "disruption_type": "other",
            "location": "Unknown",
            "title": "Manual scenario"
        }
    )

    scenarios = scenario_planning(disruption, params)
    logistics = logistics_agent(scenarios)
    inventory = inventory_agent(disruption, params)

    compliance = compliance_agent(
        sensing, scenarios, logistics
    )

    result = {
        "disruption_sensing": sensing,
        "scenario_planning": scenarios,
        "logistics": logistics,
        "inventory": inventory,
        "compliance_audit": compliance,
        "human_approval_required": compliance["review_required"]
    }

    if getattr(params, "suppliers", None):
        result["supplier_risk"] = supplier_risk_agent(params.suppliers, disruption)

    result["escalation"] = escalation_agent(sensing, compliance)
    result["explanation"] = explanation_agent(result)
    return result
