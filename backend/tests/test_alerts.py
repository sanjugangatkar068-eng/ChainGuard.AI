import main
from fastapi.testclient import TestClient

import alerting
from agents import escalation_agent

client = TestClient(main.app)


def _critical_disruption():
    return client.post("/api/disruptions", json={
        "title": "Red Sea reroute", "disruption_type": "port_closure",
        "location": "Suez Canal", "severity": "critical", "delay_days": 14,
        "estimated_loss_usd": 50000,
    }).json()["id"]


# --- threshold logic ------------------------------------------------------

def test_should_alert_respects_threshold():
    assert alerting.should_alert("critical") is True
    assert alerting.should_alert("high") is True
    assert alerting.should_alert("medium") is False
    assert alerting.should_alert("low") is False


def test_escalation_agent_escalates_critical_review():
    out = escalation_agent({"risk_level": "critical"}, {"review_required": True})
    assert out["escalate"] is True
    assert out["threshold"] == "high"


def test_escalation_agent_skips_low_risk():
    out = escalation_agent({"risk_level": "low"}, {"review_required": False})
    assert out["escalate"] is False


# --- dispatch -------------------------------------------------------------

def test_dispatch_records_log_channel_without_webhook():
    alert_id = alerting.dispatch("subject", "message", "critical", {"k": "v"})
    assert isinstance(alert_id, int)

    listing = client.get("/api/alerts").json()
    assert listing["total"] == 1
    alert = listing["items"][0]
    assert alert["channel"] == "log"
    assert alert["delivered"] is False
    assert alert["acknowledged"] is False
    assert alert["details"]["context"] == {"k": "v"}


# --- pipeline integration -------------------------------------------------

def test_analyze_dispatches_alert_for_critical():
    did = _critical_disruption()
    body = client.post("/api/analyze", json={"disruption_id": did}).json()

    assert body["escalation"]["escalate"] is True
    assert "alert_id" in body
    assert client.get("/api/alerts").json()["total"] == 1


def test_analyze_low_risk_does_not_alert():
    did = client.post("/api/disruptions", json={
        "title": "Minor blip", "disruption_type": "other",
        "location": "Nowhere", "severity": "low", "delay_days": 0,
    }).json()["id"]
    body = client.post("/api/analyze", json={"disruption_id": did}).json()

    assert body["escalation"]["escalate"] is False
    assert "alert_id" not in body
    assert client.get("/api/alerts").json()["total"] == 0


# --- acknowledge ----------------------------------------------------------

def test_acknowledge_alert():
    did = _critical_disruption()
    client.post("/api/analyze", json={"disruption_id": did})
    alert_id = client.get("/api/alerts").json()["items"][0]["id"]

    response = client.post(f"/api/alerts/{alert_id}/ack")
    assert response.status_code == 200
    assert response.json()["acknowledged"] is True
    assert client.get("/api/alerts").json()["items"][0]["acknowledged"] is True


def test_acknowledge_missing_alert_404():
    assert client.post("/api/alerts/9999/ack").status_code == 404
