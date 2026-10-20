import asyncio
import contextlib
import csv
import io
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

import alerting
import database as db
import orchestrator
from agents import signal_ingestion_agent, supplier_risk_agent
from models import (
    ApprovalDecision,
    DisruptionRequest,
    ScenarioRequest,
    SupplierRiskRequest,
)
from security import auth_enabled, require_api_key
from signals import fetch_signals

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


async def _autonomous_loop(interval):
    """Run the orchestrator on a fixed interval with no human trigger."""
    while True:
        try:
            await asyncio.to_thread(orchestrator.run_autonomous_cycle)
        except Exception:  # noqa: BLE001 - the loop must survive a failed cycle
            pass
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(_app):
    interval = orchestrator.interval_seconds()
    task = asyncio.create_task(_autonomous_loop(interval)) if interval > 0 else None
    try:
        yield
    finally:
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


app = FastAPI(
    title="ChainGuard AI",
    description="Agentic AI for resilient supply chains",
    version="1.3.0",
    lifespan=lifespan,
)

def _cors_origins():
    raw = (os.getenv("CORS_ORIGINS", "") or "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()


@app.get("/")
def home():
    return {
        "app": "ChainGuard AI",
        "status": "online",
        "docs": "/docs",
        "dashboard": "/dashboard",
        "auth": "api-key" if auth_enabled() else "open",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/dashboard")
def dashboard():
    recent = db.list_records("disruptions", 5)
    for record in recent:
        record["payload"] = json.loads(record["payload"])

    return {
        "disruptions": db.count_records("disruptions"),
        "analyses": db.count_records("analyses"),
        "approvals": db.list_records("approvals", 20),
        "recent_disruptions": recent
    }


@app.get("/api/signals")
def signals(limit: int = Query(10, ge=1, le=50)):
    """Fetch external disruption signals and classify them."""
    raw = fetch_signals(limit=limit)
    classified = signal_ingestion_agent(raw)

    db.log_event(
        "signals_ingested",
        "system",
        {"count": classified["count"], "source": classified["data_source"]}
    )

    return classified


@app.get("/api/orchestrator")
def orchestrator_status():
    """Describe the orchestrator and the roles it maintains."""
    return orchestrator.describe()


@app.post("/api/orchestrator/cycle", dependencies=[Depends(require_api_key)])
def orchestrator_cycle(limit: int = Query(5, ge=1, le=20)):
    """Run one autonomous cycle now: scan signals, act, notify. No human trigger."""
    return orchestrator.run_autonomous_cycle(limit=limit)


@app.post("/api/disruptions", dependencies=[Depends(require_api_key)])
def create_disruption(request: DisruptionRequest):
    payload = request.model_dump()

    disruption_id = db.add_record(
        "disruptions",
        "created_at, payload",
        (db.now(), json.dumps(payload))
    )

    db.log_event(
        "disruption_created",
        "user",
        {"disruption_id": disruption_id, **payload}
    )

    return {
        "id": disruption_id,
        **payload
    }


@app.get("/api/disruptions")
def list_disruptions(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    records = db.list_records("disruptions", limit, offset)

    return {
        "items": [
            {
                "id": record["id"],
                "created_at": record["created_at"],
                **json.loads(record["payload"])
            }
            for record in records
        ],
        "total": db.count_records("disruptions"),
        "limit": limit,
        "offset": offset
    }


def _load_disruption(disruption_id):
    record = db.get_record("disruptions", disruption_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail="Disruption not found"
        )
    return {
        "id": record["id"],
        **json.loads(record["payload"])
    }


@app.post("/api/analyze", dependencies=[Depends(require_api_key)])
def analyze(request: ScenarioRequest):
    disruption = None

    if request.disruption_id is not None:
        disruption = _load_disruption(request.disruption_id)

    result = orchestrator.run_pipeline(disruption, request)

    if result.get("escalation", {}).get("escalate"):
        result["alert_id"] = alerting.dispatch(
            subject=f"{result['disruption_sensing']['risk_level']} disruption",
            message=result["explanation"]["explanation"],
            level=result["disruption_sensing"]["risk_level"],
            context={
                "disruption_id": request.disruption_id,
                "recommended_action": result["logistics"]["recommended_action"],
            },
        )

    analysis_id = db.add_record(
        "analyses",
        "created_at, disruption_id, payload, status",
        (
            db.now(),
            request.disruption_id,
            json.dumps(result),
            "pending"
        )
    )

    approval_id = None

    if result["human_approval_required"]:
        approval_id = db.add_record(
            "approvals",
            "created_at, analysis_id, status",
            (db.now(), analysis_id, "pending")
        )

    db.log_event(
        "analysis_created",
        "system",
        {
            "analysis_id": analysis_id,
            "disruption_id": request.disruption_id,
            "approval_required":
                result["human_approval_required"]
        }
    )

    return {
        "analysis_id": analysis_id,
        "approval_id": approval_id,
        "status": (
            "awaiting_human_approval"
            if approval_id
            else "recommendation_ready"
        ),
        **result
    }


@app.get("/api/analyses/{analysis_id}")
def get_analysis(analysis_id: int):
    record = db.get_record("analyses", analysis_id)

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found"
        )

    return {
        **record,
        "payload": json.loads(record["payload"])
    }


@app.get("/api/approvals")
def list_approvals(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    return {
        "items": db.list_records("approvals", limit, offset),
        "total": db.count_records("approvals"),
        "limit": limit,
        "offset": offset
    }


@app.post("/api/approvals/{approval_id}/decision", dependencies=[Depends(require_api_key)])
def decide_approval(
    approval_id: int,
    request: ApprovalDecision
):
    approval = db.get_record("approvals", approval_id)

    if not approval:
        raise HTTPException(
            status_code=404,
            detail="Approval not found"
        )

    if approval["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail="Approval already decided"
        )

    status = (
        "approved"
        if request.decision == "approve"
        else "rejected"
    )

    recorded = db.decide_approval(
        approval_id,
        status,
        request.reviewer,
        request.comments
    )

    if not recorded:
        raise HTTPException(
            status_code=409,
            detail="Approval already decided"
        )

    db.log_event(
        "approval_decision",
        request.reviewer,
        {
            "approval_id": approval_id,
            "decision": status,
            "comments": request.comments
        }
    )

    return {
        "approval_id": approval_id,
        "status": status,
        "message": "Decision recorded. No external action executed."
    }


@app.get("/api/audit")
def audit_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    records = db.list_records("audit_logs", limit, offset)

    for record in records:
        record["details"] = json.loads(record["details"])

    return {
        "items": records,
        "total": db.count_records("audit_logs"),
        "limit": limit,
        "offset": offset
    }


@app.post("/api/suppliers/risk", dependencies=[Depends(require_api_key)])
def supplier_risk(request: SupplierRiskRequest):
    disruption = None

    if request.disruption_id is not None:
        disruption = _load_disruption(request.disruption_id)

    result = supplier_risk_agent(request.suppliers, disruption)

    db.log_event(
        "supplier_risk_assessed",
        "system",
        {
            "count": len(request.suppliers),
            "concentration_risk": result["concentration_risk"],
        }
    )

    return result


ANALYSES_CSV_HEADER = [
    "analysis_id", "created_at", "disruption_id", "status",
    "risk_level", "risk_score", "recommended_action",
    "extra_cost_usd", "replenishment_units", "human_approval_required",
]


def _csv_safe(value):
    """Neutralise spreadsheet formula injection (OWASP CSV injection)."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def _csv_response(header, rows, filename):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows([[_csv_safe(cell) for cell in row] for row in rows])
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/alerts")
def list_alerts(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    records = db.list_records("alerts", limit, offset)
    for record in records:
        record["details"] = json.loads(record["details"])
        record["delivered"] = bool(record["delivered"])
        record["acknowledged"] = bool(record["acknowledged"])

    return {
        "items": records,
        "total": db.count_records("alerts"),
        "limit": limit,
        "offset": offset,
    }


@app.post("/api/alerts/{alert_id}/ack", dependencies=[Depends(require_api_key)])
def acknowledge_alert(alert_id: int):
    if not db.get_record("alerts", alert_id):
        raise HTTPException(status_code=404, detail="Alert not found")

    db.ack_alert(alert_id)
    db.log_event("alert_acknowledged", "user", {"alert_id": alert_id})

    return {"alert_id": alert_id, "acknowledged": True}


@app.get("/api/export/analyses.csv")
def export_analyses():
    rows = []
    for record in db.list_records("analyses", 10000):
        payload = json.loads(record["payload"])
        sensing = payload.get("disruption_sensing", {})
        recommended = payload.get("scenario_planning", {}).get(
            "recommended_scenario", {})
        logistics = payload.get("logistics", {})
        inventory = payload.get("inventory", {})

        rows.append([
            record["id"], record["created_at"], record["disruption_id"],
            record["status"], sensing.get("risk_level"),
            sensing.get("risk_score"), logistics.get("recommended_action"),
            recommended.get("extra_cost_usd"),
            inventory.get("recommended_replenishment_units"),
            payload.get("human_approval_required"),
        ])

    return _csv_response(ANALYSES_CSV_HEADER, rows, "chainguard_analyses.csv")


@app.get("/api/export/audit.csv")
def export_audit():
    rows = [
        [r["id"], r["created_at"], r["event_type"], r["actor"], r["details"]]
        for r in db.list_records("audit_logs", 10000)
    ]
    return _csv_response(
        ["id", "created_at", "event_type", "actor", "details"],
        rows, "chainguard_audit.csv",
    )


@app.post("/api/inventory/rebalance", dependencies=[Depends(require_api_key)])
def rebalance_inventory(request: ScenarioRequest):
    disruption = None

    if request.disruption_id is not None:
        disruption = _load_disruption(request.disruption_id)

    result = orchestrator.run_pipeline(
        disruption, request
    )["inventory"]

    db.log_event(
        "inventory_recommendation",
        "system",
        result
    )

    return result


# Serve the demo dashboard (static, no build step) at /dashboard.
if STATIC_DIR.is_dir():
    app.mount(
        "/dashboard",
        StaticFiles(directory=STATIC_DIR, html=True),
        name="dashboard"
    )
