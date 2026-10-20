
import json
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import database as db
from agents import run_supply_chain_agents
from models import (
    DisruptionRequest,
    ScenarioRequest,
    ApprovalDecision
)

app = FastAPI(
    title="ChainGuard AI",
    description="Agentic AI for resilient supply chains",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_methods=["*"],
    allow_headers=["*"]
)

db.init_db()


@app.get("/")
def home():
    return {
        "app": "ChainGuard AI",
        "status": "online",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/dashboard")
def dashboard():
    return {
        "disruptions": len(db.list_records("disruptions")),
        "analyses": len(db.list_records("analyses")),
        "approvals": db.list_records("approvals", 20),
        "recent_disruptions": db.list_records("disruptions", 5)
    }


@app.post("/api/disruptions")
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
def list_disruptions():
    records = db.list_records("disruptions")

    return {
        "items": [
            {
                "id": record["id"],
                "created_at": record["created_at"],
                **json.loads(record["payload"])
            }
            for record in records
        ]
    }


@app.post("/api/analyze")
def analyze(request: ScenarioRequest):
    disruption = None

    if request.disruption_id is not None:
        record = db.get_record(
            "disruptions", request.disruption_id
        )

        if not record:
            raise HTTPException(
                status_code=404,
                detail="Disruption not found"
            )

        disruption = {
            "id": record["id"],
            **json.loads(record["payload"])
        }

    result = run_supply_chain_agents(disruption, request)

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
def list_approvals():
    return {"items": db.list_records("approvals")}


@app.post("/api/approvals/{approval_id}/decision")
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

    with sqlite3.connect(db.DB_NAME) as conn:
        conn.execute(
            """
            UPDATE approvals
            SET status=?, reviewer=?, comments=?, decided_at=?
            WHERE id=? AND status='pending'
            """,
            (
                status,
                request.reviewer,
                request.comments,
                db.now(),
                approval_id
            )
        )

        conn.execute(
            "UPDATE analyses SET status=? WHERE id=?",
            (status, approval["analysis_id"])
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
def audit_logs():
    records = db.list_records("audit_logs")

    for record in records:
        record["details"] = json.loads(record["details"])

    return {"items": records}


@app.post("/api/inventory/rebalance")
def rebalance_inventory(request: ScenarioRequest):
    disruption = None

    if request.disruption_id is not None:
        record = db.get_record(
            "disruptions", request.disruption_id
        )

        if not record:
            raise HTTPException(
                status_code=404,
                detail="Disruption not found"
            )

        disruption = {
            "id": record["id"],
            **json.loads(record["payload"])
        }

    result = run_supply_chain_agents(
        disruption, request
    )["inventory"]

    db.log_event(
        "inventory_recommendation",
        "system",
        result
    )

    return result
