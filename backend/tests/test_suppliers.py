from fastapi.testclient import TestClient

import main
from agents import (
    disruption_sensing,
    logistics_agent,
    scenario_planning,
    supplier_risk_agent,
)
from models import ScenarioRequest, Supplier

client = TestClient(main.app)

SUPPLIERS = [
    Supplier(name="Apex Components", tier=1, country="China",
             single_source=True, lead_time_days=21, spend_usd=120000),
    Supplier(name="Baltic Metals", tier=2, country="Poland",
             single_source=False, lead_time_days=12, spend_usd=40000),
    Supplier(name="Deccan Plastics", tier=1, country="India",
             single_source=False, lead_time_days=9, spend_usd=60000),
]


# --- supplier risk agent --------------------------------------------------

def test_supplier_risk_flags_concentration():
    out = supplier_risk_agent(SUPPLIERS)
    assert out["agent"] == "Supplier Risk Agent"
    # Apex is 120k of 220k spend = ~54.5% -> concentration risk
    assert out["concentration_risk"] is True
    assert out["top_supplier"] == "Apex Components"


def test_supplier_risk_scores_single_source_highest():
    out = supplier_risk_agent(SUPPLIERS)
    assert out["highest_risk_supplier"] == "Apex Components"
    apex = next(s for s in out["suppliers"] if s["name"] == "Apex Components")
    assert apex["risk_level"] in ("high", "critical")
    assert apex["single_source"] is True


def test_supplier_risk_balanced_spend_no_concentration():
    balanced = [
        Supplier(name="Alpha", spend_usd=100),
        Supplier(name="Beta", spend_usd=100),
        Supplier(name="Gamma", spend_usd=100),
    ]
    out = supplier_risk_agent(balanced)
    assert out["concentration_risk"] is False


def test_supplier_risk_country_matches_disruption_location():
    suppliers = [Supplier(name="Local Co", country="India", spend_usd=100)]
    low = supplier_risk_agent(suppliers)["suppliers"][0]["risk_score"]
    high = supplier_risk_agent(
        suppliers, {"location": "India"}
    )["suppliers"][0]["risk_score"]
    assert high > low


# --- enriched agent outputs -----------------------------------------------

def test_sensing_reports_confidence_and_source():
    out = disruption_sensing({"severity": "critical", "delay_days": 14,
                              "disruption_type": "port_closure",
                              "location": "Suez", "title": "t",
                              "estimated_loss_usd": 5000})
    assert out["confidence"] == 1.0
    assert out["source"] == "user-provided demo data"


def test_logistics_reports_route_and_eta():
    params = ScenarioRequest()
    planning = scenario_planning({"delay_days": 10, "tariff_percent": 0,
                                  "estimated_loss_usd": 0}, params)
    out = logistics_agent(planning)
    assert "recommended_route" in out
    assert out["revised_eta_days"] == out["estimated_delay_days"]


# --- endpoints ------------------------------------------------------------

def test_suppliers_risk_endpoint():
    body = client.post("/api/suppliers/risk", json={
        "suppliers": [s.model_dump() for s in SUPPLIERS],
    }).json()
    assert body["concentration_risk"] is True
    assert len(body["suppliers"]) == 3


def test_analyze_includes_supplier_risk_when_provided():
    did = client.post("/api/disruptions", json={
        "title": "Red Sea reroute", "disruption_type": "port_closure",
        "location": "Suez Canal", "severity": "critical", "delay_days": 14,
    }).json()["id"]

    with_suppliers = client.post("/api/analyze", json={
        "disruption_id": did,
        "suppliers": [s.model_dump() for s in SUPPLIERS],
    }).json()
    assert "supplier_risk" in with_suppliers
    assert with_suppliers["supplier_risk"]["agent"] == "Supplier Risk Agent"

    without = client.post("/api/analyze", json={"disruption_id": did}).json()
    assert "supplier_risk" not in without
