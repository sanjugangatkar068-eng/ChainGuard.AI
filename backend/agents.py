import json
from math import ceil

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

    if score >= 80:
        level = "critical"
    elif score >= 60:
        level = "high"
    elif score >= 35:
        level = "medium"
    else:
        level = "low"

    return {
        "agent": "Disruption Sensing Agent",
        "risk_score": score,
        "risk_level": level,
        "disruption_type": disruption.get("disruption_type", "other"),
        "location": disruption.get("location", "Unknown"),
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
        "estimated_cost_usd": selected["extra_cost_usd"],
        "estimated_delay_days": selected["delay_days"],
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

    return {
        "agent": "Compliance & Audit Agent",
        "review_required": bool(flags),
        "flags": flags,
        "decision_logged": True
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
    logistics = result["logistics"]
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
        f"(score {sensing['risk_score']}/100). "
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

    result["explanation"] = explanation_agent(result)
    return result
