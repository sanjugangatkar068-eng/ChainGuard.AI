import main
from fastapi.testclient import TestClient

client = TestClient(main.app)


def _make_analysis():
    did = client.post("/api/disruptions", json={
        "title": "Red Sea reroute", "disruption_type": "port_closure",
        "location": "Suez Canal", "severity": "critical", "delay_days": 14,
        "estimated_loss_usd": 50000,
    }).json()["id"]
    return client.post("/api/analyze", json={"disruption_id": did}).json()


def test_export_analyses_csv_headers():
    response = client.get("/api/export/analyses.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]


def test_export_analyses_csv_rows():
    _make_analysis()
    response = client.get("/api/export/analyses.csv")
    lines = [line for line in response.text.strip().splitlines() if line]

    assert lines[0].startswith("analysis_id,created_at,disruption_id")
    assert len(lines) == 2  # header + one analysis
    # the critical disruption should be exported with its risk level
    assert "critical" in lines[1]


def test_export_audit_csv():
    _make_analysis()
    response = client.get("/api/export/audit.csv")
    assert response.status_code == 200
    lines = [line for line in response.text.strip().splitlines() if line]
    assert lines[0].startswith("id,created_at,event_type,actor")
    assert len(lines) >= 2
