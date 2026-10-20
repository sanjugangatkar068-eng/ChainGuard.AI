
from math import ceil


def disruption_sensing(disruption):
    severity_scores = {
        "low": 20,
        "medium": 45,
        "high": 75,
        "critical": 95
    }

    score = severity_scores[disruption["severity"]]
    score = min(100, score + disruption["delay_days"])

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
        "disruption_type": disruption["disruption_type"],
        "location": disruption["location"],
        "signals": [
            disruption["title"],
            f"Delay: {disruption['delay_days']} days",
            f"Severity: {disruption['severity']}"
        ],
        "data_source": "User-provided demo data"
    }


def scenario_planning(disruption, params):
    delay = disruption["delay_days"] if disruption else 0
    tariff = disruption["tariff_percent"] if disruption else 0
    loss = disruption["estimated_loss_usd"] if disruption else 0

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
    delay = disruption["delay_days"] if disruption else 0

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

    return {
        "disruption_sensing": sensing,
        "scenario_planning": scenarios,
        "logistics": logistics,
        "inventory": inventory,
        "compliance_audit": compliance,
        "human_approval_required": compliance["review_required"]
    }
