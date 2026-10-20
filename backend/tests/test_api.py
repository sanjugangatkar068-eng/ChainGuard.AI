from fastapi.testclient import TestClient

import main
from agents import disruption_sensing, scenario_planning, run_supply_chain_agents
from models import ScenarioRequest

client = TestClient(main.app)


def make_disruption(**overrides):
    body = {
        "title": "Red Sea reroute",
        "disruption_type": "port_closure",
        "location": "Suez Canal",
        "severity": "critical",
        "delay_days": 14,
        "estimated_loss_usd": 50000,
    }
    body.update(overrides)
    return client.post("/api/disruptions", json=body)


# --- basics ---------------------------------------------------------------

def test_home_and_health():
    assert client.get("/").json()["status"] == "online"
    assert client.get("/health").json() == {"status": "healthy"}


def test_dashboard_starts_empty():
    body = client.get("/api/dashboard").json()
    assert body["disruptions"] == 0
    assert body["analyses"] == 0
    assert body["recent_disruptions"] == []


# --- disruptions ----------------------------------------------------------

def test_create_and_list_disruption():
    created = make_disruption().json()
    assert created["id"] == 1
    assert created["severity"] == "critical"

    listed = client.get("/api/disruptions").json()
    assert listed["total"] == 1
    assert listed["items"][0]["title"] == "Red Sea reroute"


def test_create_disruption_validates_input():
    bad = client.post("/api/disruptions", json={
        "title": "no",  # too short
        "disruption_type": "port_closure",
        "location": "X",
    })
    assert bad.status_code == 422


# --- pagination -----------------------------------------------------------

def test_pagination_limit_offset_and_total():
    for i in range(7):
        make_disruption(title=f"event {i}")

    page1 = client.get("/api/disruptions?limit=3&offset=0").json()
    page2 = client.get("/api/disruptions?limit=3&offset=3").json()

    assert page1["total"] == 7
    assert len(page1["items"]) == 3
    assert len(page2["items"]) == 3
    # newest first, so pages must not overlap
    assert {i["id"] for i in page1["items"]}.isdisjoint(
        {i["id"] for i in page2["items"]}
    )


def test_pagination_rejects_bad_limit():
    assert client.get("/api/disruptions?limit=0").status_code == 422


# --- analysis + approval --------------------------------------------------

def test_analyze_critical_requires_approval():
    did = make_disruption().json()["id"]
    body = client.post("/api/analyze", json={"disruption_id": did}).json()

    assert body["status"] == "awaiting_human_approval"
    assert body["human_approval_required"] is True
    assert body["approval_id"] is not None
    assert body["disruption_sensing"]["risk_level"] == "critical"


def test_analyze_unknown_disruption_404():
    assert client.post("/api/analyze", json={"disruption_id": 999}).status_code == 404


def test_analyze_without_disruption_ok():
    body = client.post("/api/analyze", json={}).json()
    assert body["human_approval_required"] is False
    assert body["status"] == "recommendation_ready"


def test_approval_decision_updates_analysis_and_blocks_double_decide():
    did = make_disruption().json()["id"]
    analysis = client.post("/api/analyze", json={"disruption_id": did}).json()
    aid = analysis["approval_id"]
    analysis_id = analysis["analysis_id"]

    first = client.post(f"/api/approvals/{aid}/decision", json={
        "decision": "approve", "reviewer": "Meghana", "comments": "ok",
    })
    assert first.status_code == 200
    assert first.json()["status"] == "approved"

    second = client.post(f"/api/approvals/{aid}/decision", json={
        "decision": "reject", "reviewer": "Meghana",
    })
    assert second.status_code == 409

    stored = client.get(f"/api/analyses/{analysis_id}").json()
    assert stored["status"] == "approved"


def test_approval_decision_404():
    assert client.post("/api/approvals/999/decision", json={
        "decision": "approve", "reviewer": "Meghana",
    }).status_code == 404


# --- audit + inventory ----------------------------------------------------

def test_audit_records_events():
    make_disruption()
    events = client.get("/api/audit").json()
    assert events["total"] >= 1
    assert events["items"][0]["event_type"] == "disruption_created"


def test_inventory_rebalance():
    did = make_disruption().json()["id"]
    body = client.post("/api/inventory/rebalance", json={"disruption_id": did}).json()
    assert body["recommended_replenishment_units"] == 120
    assert body["projected_inventory"] == 0


# --- agent unit tests -----------------------------------------------------

def test_sensing_score_is_capped_and_classified():
    out = disruption_sensing({"severity": "critical", "delay_days": 90,
                              "disruption_type": "port_closure",
                              "location": "Suez", "title": "t"})
    assert out["risk_score"] == 100
    assert out["risk_level"] == "critical"


def test_scenario_planning_prefers_lowest_delay_within_budget():
    params = ScenarioRequest(disruption_id=None, max_budget_usd=10_000_000)
    out = scenario_planning({"delay_days": 14, "tariff_percent": 0,
                             "estimated_loss_usd": 0}, params)
    assert out["recommended_scenario"]["id"] == "expedite"
    assert all(s["within_budget"] for s in out["scenarios"])


def test_pipeline_flags_budget_breach():
    params = ScenarioRequest(disruption_id=None, max_budget_usd=10)
    out = run_supply_chain_agents({"severity": "low", "delay_days": 1,
                                   "disruption_type": "other", "location": "X",
                                   "title": "t", "tariff_percent": 0,
                                   "estimated_loss_usd": 1000}, params)
    assert out["compliance_audit"]["review_required"] is True
    assert "All scenarios exceed the configured budget." in out["compliance_audit"]["flags"]
