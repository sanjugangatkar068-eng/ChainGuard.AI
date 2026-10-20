import main
from fastapi.testclient import TestClient

import security

client = TestClient(main.app)

DISRUPTION = {
    "title": "Red Sea reroute",
    "disruption_type": "port_closure",
    "location": "Suez Canal",
    "severity": "critical",
    "delay_days": 14,
}


# --- API-key authentication ----------------------------------------------

def test_auth_disabled_by_default():
    assert security.auth_enabled() is False
    assert client.get("/").json()["auth"] == "open"
    assert client.post("/api/disruptions", json=DISRUPTION).status_code == 200


def test_mutating_endpoints_require_key_when_configured(monkeypatch):
    monkeypatch.setenv("API_KEY", "s3cret-value")
    assert security.auth_enabled() is True

    # no header
    assert client.post("/api/disruptions", json=DISRUPTION).status_code == 401
    # wrong header
    assert client.post(
        "/api/disruptions", json=DISRUPTION, headers={"X-API-Key": "wrong"}
    ).status_code == 401
    # correct header
    ok = client.post(
        "/api/disruptions", json=DISRUPTION, headers={"X-API-Key": "s3cret-value"}
    )
    assert ok.status_code == 200

    # the banner advertises that auth is on
    assert client.get("/").json()["auth"] == "api-key"


def test_read_endpoints_stay_open_with_key_configured(monkeypatch):
    monkeypatch.setenv("API_KEY", "s3cret-value")
    assert client.get("/api/dashboard").status_code == 200
    assert client.get("/api/disruptions").status_code == 200
    assert client.get("/health").status_code == 200


def test_all_mutating_endpoints_are_protected(monkeypatch):
    monkeypatch.setenv("API_KEY", "s3cret-value")
    protected = [
        ("post", "/api/disruptions", DISRUPTION),
        ("post", "/api/analyze", {"disruption_id": 1}),
        ("post", "/api/approvals/1/decision",
         {"decision": "approve", "reviewer": "tester"}),
        ("post", "/api/alerts/1/ack", None),
        ("post", "/api/suppliers/risk", {"suppliers": []}),
        ("post", "/api/inventory/rebalance", {}),
        ("post", "/api/orchestrator/cycle", None),
    ]
    for method, path, body in protected:
        response = getattr(client, method)(path, json=body)
        assert response.status_code == 401, f"{path} was not protected"


# --- CSV formula injection ------------------------------------------------

def test_csv_safe_helper():
    assert main._csv_safe("=SUM(A1)") == "'=SUM(A1)"
    assert main._csv_safe("+1") == "'+1"
    assert main._csv_safe("-cmd") == "'-cmd"
    assert main._csv_safe("@x") == "'@x"
    assert main._csv_safe("normal") == "normal"
    assert main._csv_safe(42) == 42          # numbers are left alone
    assert main._csv_safe(None) is None


def test_csv_export_neutralises_formula_injection():
    did = client.post("/api/disruptions", json=DISRUPTION).json()["id"]
    analysis = client.post("/api/analyze", json={"disruption_id": did}).json()
    approval_id = analysis["approval_id"]

    client.post(
        f"/api/approvals/{approval_id}/decision",
        json={"decision": "approve", "reviewer": "=SUM(1+1)", "comments": "x"},
    )

    csv_text = client.get("/api/export/audit.csv").text
    assert "'=SUM(1+1)" in csv_text       # neutralised
    assert ",=SUM(1+1)" not in csv_text   # never a bare formula at cell start


# --- input bounds ---------------------------------------------------------

def test_oversized_input_is_rejected():
    too_long = dict(DISRUPTION, description="x" * 5000)
    assert client.post("/api/disruptions", json=too_long).status_code == 422

    too_long_title = dict(DISRUPTION, title="x" * 500)
    assert client.post("/api/disruptions", json=too_long_title).status_code == 422
