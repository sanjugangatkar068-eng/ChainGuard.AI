"""Populate the database with demo data for a walkthrough or pitch.

Usage (from the backend/ folder):

    python seed.py            # add demo data on top of what exists
    python seed.py --reset    # clear the tables first
"""

import argparse
import json

import database as db
from agents import run_supply_chain_agents
from models import DisruptionRequest, ScenarioRequest, Supplier

DEMO_DISRUPTIONS = [
    {
        "title": "Red Sea reroute after canal disruption",
        "disruption_type": "port_closure",
        "location": "Suez Canal",
        "severity": "critical",
        "description": "Carriers divert around the Cape of Good Hope.",
        "delay_days": 14,
        "estimated_loss_usd": 50000,
    },
    {
        "title": "US tariff increase on imported components",
        "disruption_type": "tariff_change",
        "location": "United States",
        "severity": "high",
        "description": "New duties raise landed cost on key parts.",
        "delay_days": 5,
        "tariff_percent": 25,
        "estimated_loss_usd": 20000,
    },
    {
        "title": "Port congestion at a major gateway",
        "disruption_type": "port_congestion",
        "location": "Rotterdam",
        "severity": "medium",
        "description": "Vessel queues build; berthing windows slip.",
        "delay_days": 6,
        "estimated_loss_usd": 8000,
    },
    {
        "title": "Cyclone closes supplier plant",
        "disruption_type": "supplier_outage",
        "location": "India",
        "severity": "high",
        "description": "Production halted at a single-source plant.",
        "delay_days": 9,
        "estimated_loss_usd": 30000,
    },
]

DEMO_SUPPLIERS = [
    {"name": "Apex Components", "tier": 1, "country": "China",
     "single_source": True, "lead_time_days": 21, "spend_usd": 120000},
    {"name": "Baltic Metals", "tier": 2, "country": "Poland",
     "single_source": False, "lead_time_days": 12, "spend_usd": 40000},
    {"name": "Deccan Plastics", "tier": 1, "country": "India",
     "single_source": False, "lead_time_days": 9, "spend_usd": 60000},
    {"name": "Pacific Fasteners", "tier": 3, "country": "Vietnam",
     "single_source": False, "lead_time_days": 18, "spend_usd": 25000},
]


def reset_tables():
    with db.get_conn() as conn:
        for table in ("disruptions", "analyses", "approvals", "audit_logs"):
            conn.execute(f"DELETE FROM {table}")


def seed(reset=False):
    """Insert demo disruptions, run the agent pipeline, and return a summary."""
    db.init_db()
    if reset:
        reset_tables()

    suppliers = [Supplier(**s) for s in DEMO_SUPPLIERS]
    disruptions = analyses = approvals = 0

    for raw in DEMO_DISRUPTIONS:
        payload = DisruptionRequest(**raw).model_dump()

        disruption_id = db.add_record(
            "disruptions",
            "created_at, payload",
            (db.now(), json.dumps(payload)),
        )
        disruptions += 1

        db.log_event("disruption_created", "seed",
                     {"disruption_id": disruption_id, **payload})

        params = ScenarioRequest(
            disruption_id=disruption_id, suppliers=suppliers)
        disruption = {"id": disruption_id, **payload}
        result = run_supply_chain_agents(disruption, params)

        analysis_id = db.add_record(
            "analyses",
            "created_at, disruption_id, payload, status",
            (db.now(), disruption_id, json.dumps(result), "pending"),
        )
        analyses += 1

        if result["human_approval_required"]:
            db.add_record(
                "approvals",
                "created_at, analysis_id, status",
                (db.now(), analysis_id, "pending"),
            )
            approvals += 1

        db.log_event("analysis_created", "seed", {
            "analysis_id": analysis_id,
            "disruption_id": disruption_id,
            "approval_required": result["human_approval_required"],
        })

    return {
        "disruptions": disruptions,
        "analyses": analyses,
        "approvals": approvals,
        "suppliers": len(suppliers),
    }


def main():
    parser = argparse.ArgumentParser(description="Seed ChainGuard AI demo data.")
    parser.add_argument("--reset", action="store_true",
                        help="clear existing tables before seeding")
    args = parser.parse_args()

    summary = seed(reset=args.reset)
    print(
        f"Seeded {summary['disruptions']} disruptions, "
        f"{summary['analyses']} analyses, "
        f"{summary['approvals']} approvals "
        f"({summary['suppliers']} suppliers each)."
    )
    print(f"Database: {db.DB_NAME}")


if __name__ == "__main__":
    main()
