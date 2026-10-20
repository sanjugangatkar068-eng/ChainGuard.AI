import main
from fastapi.testclient import TestClient

import orchestrator
from models import ScenarioRequest

client = TestClient(main.app)

SIGNALS = [
    {
        "title": "Canal closure halts container shipping",
        "summary": "Carriers reroute around the Cape.",
        "link": "",
        "published": None,
        "source": "test",
    },
    {
        "title": "Retailer announces quarterly dividend",
        "summary": "Unrelated to supply chains.",
        "link": "",
        "published": None,
        "source": "test",
    },
]


# --- the pipeline coordinator --------------------------------------------

def test_pipeline_runs_every_role_and_records_a_trace():
    result = orchestrator.run_pipeline(None, ScenarioRequest())

    statuses = {step["agent"]: step["status"] for step in result["pipeline"]["trace"]}
    assert statuses["disruption_sensing"] == "ok"
    assert statuses["compliance_audit"] == "ok"
    assert statuses["escalation"] == "ok"
    # explanation must run even when human_approval_required is False
    assert statuses["explanation"] == "ok"
    assert result["pipeline"]["agents_failed"] == 0
    assert result["pipeline"]["orchestrator"] == "ChainGuard Orchestrator"


def test_pipeline_tolerates_a_failing_role(monkeypatch):
    def boom(_disruption):
        raise RuntimeError("sensor offline")

    monkeypatch.setattr(orchestrator, "disruption_sensing", boom)

    result = orchestrator.run_pipeline(None, ScenarioRequest())
    trace = {step["agent"]: step for step in result["pipeline"]["trace"]}

    assert trace["disruption_sensing"]["status"] == "error"
    assert "sensor offline" in trace["disruption_sensing"]["error"]
    # dependents are skipped rather than crashing the request
    assert trace["scenario_planning"]["status"] == "skipped"
    assert result["pipeline"]["agents_failed"] == 1
    assert result["pipeline"]["agents_skipped"] >= 1


def test_describe_lists_roles_and_mode():
    info = orchestrator.describe()
    assert info["orchestrator"] == "ChainGuard Orchestrator"
    assert info["mode"] == "on-demand"
    keys = {role["key"] for role in info["roles"]}
    assert {"disruption_sensing", "scenario_planning", "compliance_audit"} <= keys


def test_orchestrator_status_endpoint():
    body = client.get("/api/orchestrator").json()
    assert body["mode"] == "on-demand"
    assert body["roles"]


# --- autonomous, no-human-trigger cycle -----------------------------------

def test_autonomous_cycle_acts_and_notifies(monkeypatch):
    monkeypatch.setattr(orchestrator, "fetch_signals", lambda limit=10: SIGNALS)

    summary = orchestrator.run_autonomous_cycle(limit=5)

    assert summary["scanned"] == 2
    assert summary["relevant"] == 1          # the weather item is not supply-chain relevant
    assert summary["created"] == 1
    assert summary["escalated"] == 1
    assert summary["notified"] == 1

    # it raised an alert with no human involvement
    assert client.get("/api/alerts").json()["total"] == 1
    # and it left a reviewable approval behind
    assert client.get("/api/approvals").json()["total"] == 1


def test_autonomous_cycle_deduplicates(monkeypatch):
    monkeypatch.setattr(orchestrator, "fetch_signals", lambda limit=10: SIGNALS)

    first = orchestrator.run_autonomous_cycle()
    second = orchestrator.run_autonomous_cycle()

    assert first["created"] == 1
    assert second["created"] == 0


def test_autonomous_cycle_offline_sample_is_safe(monkeypatch):
    # when no feed is reachable, fetch_signals returns the offline sample
    monkeypatch.setattr(
        orchestrator, "fetch_signals",
        lambda limit=10: [{"title": "Port congestion builds", "summary": "",
                           "link": "", "published": None, "source": "sample"}],
    )
    summary = orchestrator.run_autonomous_cycle()
    assert summary["data_source"] == "Offline sample"
    assert summary["created"] == 1


def test_orchestrator_cycle_endpoint(monkeypatch):
    monkeypatch.setattr(orchestrator, "fetch_signals", lambda limit=10: SIGNALS)

    body = client.post("/api/orchestrator/cycle?limit=5").json()

    assert body["created"] == 1
    assert body["notified"] == 1
    assert body["items"][0]["alert_id"] is not None


def test_analyze_includes_pipeline_trace():
    did = client.post("/api/disruptions", json={
        "title": "Red Sea reroute", "disruption_type": "port_closure",
        "location": "Suez Canal", "severity": "critical", "delay_days": 14,
    }).json()["id"]

    body = client.post("/api/analyze", json={"disruption_id": did}).json()

    assert "pipeline" in body
    assert body["pipeline"]["agents_failed"] == 0
