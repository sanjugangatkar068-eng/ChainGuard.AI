# ChainGuard AI

**Agentic AI for resilient supply chains.**

ChainGuard AI is a FastAPI backend that models the "Resilient Supply Chains" hackathon
theme as a pipeline of collaborating agents. It senses a disruption, plans response
scenarios, recommends logistics and inventory actions, flags compliance concerns, and
routes high-stakes decisions to a human for approval — logging everything to an
audit trail.

> All outputs are **recommendations only**. The system never executes an external
> action (no bookings, no orders); a human decision is required for high-risk cases.

## Agent pipeline

| Agent | Role |
| --- | --- |
| Disruption Sensing Agent | Scores a disruption's severity into a risk level. |
| Scenario Planning Agent | Compares wait / reroute / expedite options on cost and delay, within budget. |
| Rerouting & Logistics Agent | Turns the chosen scenario into a concrete recommended action. |
| Inventory Rebalancing Agent | Recomputes reorder point and replenishment needs. |
| Compliance & Audit Agent | Flags high-risk cases and budget breaches; decides if human approval is required. |

## Requirements

- Python 3.12+
- See `backend/requirements.txt`

## Setup

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env      # then edit if needed
```

## Run

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Open http://127.0.0.1:8000/docs for the interactive API docs.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Service banner. |
| GET | `/health` | Health check. |
| GET | `/api/dashboard` | Counts plus recent disruptions and approvals. |
| POST | `/api/disruptions` | Create a disruption record. |
| GET | `/api/disruptions` | List disruptions. |
| POST | `/api/analyze` | Run the agent pipeline for a scenario. |
| GET | `/api/analyses/{id}` | Fetch a stored analysis. |
| GET | `/api/approvals` | List approval requests. |
| POST | `/api/approvals/{id}/decision` | Approve or reject a request. |
| GET | `/api/audit` | Read the audit log. |
| POST | `/api/inventory/rebalance` | Inventory recommendation only. |

## Quick example

```bash
# 1. Create a disruption
curl -X POST http://127.0.0.1:8000/api/disruptions \
  -H "Content-Type: application/json" \
  -d '{"title":"Red Sea reroute","disruption_type":"port_closure",
       "location":"Suez Canal","severity":"critical","delay_days":14,
       "estimated_loss_usd":50000}'

# 2. Analyze it (use the returned id)
curl -X POST http://127.0.0.1:8000/api/analyze \
  -H "Content-Type: application/json" -d '{"disruption_id":1}'

# 3. Decide the approval (use the returned approval_id)
curl -X POST http://127.0.0.1:8000/api/approvals/1/decision \
  -H "Content-Type: application/json" \
  -d '{"decision":"approve","reviewer":"Meghana","comments":"reroute approved"}'
```

## Project structure

```
.
├── .gitignore
├── README.md
└── backend
    ├── main.py           # FastAPI app and routes
    ├── agents.py         # agent pipeline
    ├── models.py         # Pydantic request models
    ├── database.py       # SQLite helpers
    ├── requirements.txt
    └── .env.example
```

## Configuration

`.env` (copied from `.env.example`) supports:

- `APP_NAME` — display name.
- `DATABASE_PATH` — SQLite file path; relative paths resolve to the `backend/` folder.

## Notes

- The SQLite database (`chainguard.db`) is created on first run and is **not**
  committed to git.
- `.env` holds local config and is git-ignored; only `.env.example` is tracked.
