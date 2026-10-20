# ChainGuard AI — Architecture

## Overview

ChainGuard AI is a FastAPI service that turns a supply-chain disruption into a
reviewed, audited recommendation. It is deliberately **recommendation-only**: no
external action (booking, ordering, rerouting) is ever executed automatically. A human
approves high-risk decisions.

The design follows the hackathon theme's "collaborating agents" model — each agent has
a clear role, defined inputs/outputs, and an explicit handoff point.

## Component map

```
                    ┌────────────────────────────────────────────┐
   RSS / Atom ──────►  Disruption Sensing Agent                    │
   feeds              │  classify headline → type, severity,      │
                      │  confidence, source                       │
                      └───────────────────────┬────────────────────┘
                                              │
   Disruption ────────────────────────────────┤
   (user input)                               ▼
                      ┌────────────────────────────────────────────┐
                      │  Scenario Planning Agent                   │
                      │  wait / reroute / expedite → cost, delay,  │
                      │  risk, budget fit                          │
                      └───────────────────────┬────────────────────┘
                                              │
              ┌───────────────────────────────┼───────────────────────────────┐
              ▼                               ▼                               ▼
   ┌────────────────────┐        ┌────────────────────┐        ┌────────────────────┐
   │ Rerouting &        │        │ Inventory          │        │ Supplier Risk      │
   │ Logistics Agent    │        │ Rebalancing Agent  │        │ Agent              │
   │ route + ETA + cost │        │ reorder + replenish│        │ exposure + concen. │
   └─────────┬──────────┘        └─────────┬──────────┘        └─────────┬──────────┘
             └───────────────────────────────┼───────────────────────────────┘
                                             ▼
                      ┌────────────────────────────────────────────┐
                      │  Compliance & Audit Agent                  │
                      │  flags, report, review_required            │
                      └───────────────────────┬────────────────────┘
                                              │
                      ┌───────────────────────┴────────────────────┐
                      ▼                                            ▼
          Explanation Agent                       Human-in-the-loop approval
          (LLM if configured, else rules)         (pending → approved / rejected)
```

## Agents

| Agent | Input | Output |
| --- | --- | --- |
| Orchestrator | disruption + parameters | runs every role in order; trace, counts, timing |
| Disruption Sensing | Feed items or a disruption record | disruption type, severity, risk score, confidence, source |
| Scenario Planning | disruption + inventory parameters | scenarios (cost, delay, risk, budget fit) + recommendation |
| Rerouting & Logistics | recommended scenario | action, route, revised ETA, cost |
| Inventory Rebalancing | disruption + parameters | reorder point, projected stock, replenishment units |
| Supplier Risk | supplier network | per-supplier risk score, spend share, concentration flag |
| Compliance & Audit | sensing + scenarios + logistics | flags, report, `review_required` |
| Escalation | sensing + compliance | whether to alert, threshold, reason |
| Explanation | the whole result | plain-language rationale (`llm` or `rules`) |

## Request flow (`POST /api/analyze`)

1. Optionally load a stored disruption by `disruption_id`.
2. Run the agent pipeline in `agents.run_supply_chain_agents`.
3. Persist the analysis to `analyses`.
4. If `human_approval_required`, create a row in `approvals` and return status
   `awaiting_human_approval`.
5. Append an audit event.
6. The reviewer calls `POST /api/approvals/{id}/decision`; the approval and its linked
   analysis are updated atomically, and another audit event is written.

## Data model (SQLite)

| Table | Columns |
| --- | --- |
| `disruptions` | id, created_at, payload (JSON) |
| `analyses` | id, created_at, disruption_id, payload (JSON), status |
| `approvals` | id, created_at, analysis_id, status, reviewer, comments, decided_at |
| `audit_logs` | id, created_at, event_type, actor, details (JSON) |
| `alerts` | id, created_at, level, subject, message, channel, delivered, acknowledged, details (JSON) |

Connections are opened per operation through a `get_conn()` context manager that
commits on success, rolls back on error, and always closes.

## Autonomous operation

`orchestrator.run_autonomous_cycle()` is the no-human path: it ingests signals, raises
a de-duplicated disruption per relevant headline, runs `run_pipeline`, creates an
approval when review is required and dispatches a notification when the Escalation
Agent fires. `main.py` runs it on a background `asyncio` task when
`ORCHESTRATOR_INTERVAL_SECONDS > 0` (started in the FastAPI lifespan, cancelled on
shutdown), or on demand via `POST /api/orchestrator/cycle`.

A failing role is recorded in the trace with `status: "error"`; roles depending on it
are marked `"skipped"` rather than crashing the request.

## Configuration

All configuration is environment-driven (see `.env.example`): database path, optional
LLM provider/key/model, and signal feed URLs. **No secrets are hardcoded.** With no LLM
configured the Explanation Agent falls back to a deterministic template, so the service
always runs.

## Failure handling

- Feed fetch: each feed is tried independently; total failure returns an offline sample.
- LLM: any provider error falls back to rules-based reasoning.
- Data: list endpoints paginate; counts use `COUNT(*)`, not list length.

## Tests

`pytest` covers the agent pipeline, validation, pagination, the approval state machine,
feed parsing, LLM fallback, supplier scoring, and the seed script. CI runs the suite on
every push and pull request.
