# ChainGuard AI

**Agentic AI for resilient supply chains.**

ChainGuard AI is a FastAPI backend that models the "Resilient Supply Chains" hackathon
theme as a pipeline of collaborating agents. It ingests external disruption signals,
senses risk, plans response scenarios, recommends logistics and inventory actions,
flags compliance concerns, and routes high-stakes decisions to a human for approval —
logging everything to an audit trail. A zero-build demo dashboard ships with it.

> All outputs are **recommendations only**. The system never executes an external
> action (no bookings, no orders); a human decision is required for high-risk cases.

## Agent pipeline

| Agent | Role |
| --- | --- |
| Disruption Sensing Agent | Ingests RSS/Atom feeds, classifies headlines, and scores a disruption's severity. |
| Scenario Planning Agent | Compares wait / reroute / expedite options on cost and delay, within budget. |
| Rerouting & Logistics Agent | Turns the chosen scenario into a concrete recommended action. |
| Inventory Rebalancing Agent | Recomputes reorder point and replenishment needs. |
| Compliance & Audit Agent | Flags high-risk cases and budget breaches; decides if human approval is required. |
| Explanation Agent | Narrates the assessment in plain language (LLM if configured, else rules). |
| Human-in-the-loop | A reviewer approves or rejects high-risk recommendations. |

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

pip install -r requirements-dev.txt   # includes runtime + test deps
cp .env.example .env                  # then edit if needed
```

## Run

```bash
cd backend
uvicorn main:app --reload --port 8000
```

- Interactive API docs: http://127.0.0.1:8000/docs
- Demo dashboard: http://127.0.0.1:8000/dashboard

## Configuration

Copy `.env.example` to `.env`. Everything is optional — with no configuration the
app runs on rules-based reasoning and default feeds.

| Variable | Purpose |
| --- | --- |
| `APP_NAME` | Display name. |
| `DATABASE_PATH` | SQLite file path; relative paths resolve to `backend/`. |
| `LLM_PROVIDER` | `none` (default), `openai`, or `anthropic`. |
| `LLM_API_KEY` | Provider API key. **Never commit this.** |
| `LLM_MODEL` | Optional model override. |
| `LLM_BASE_URL` | Optional base URL (for OpenAI-compatible endpoints). |
| `SIGNAL_FEEDS` | Comma-separated RSS/Atom feed URLs. |

**LLM reasoning is optional.** With `LLM_PROVIDER=none` (or no key), the Explanation
Agent uses a deterministic template, so the app always works. Set a provider and key
to get natural-language rationales. The key is read from the environment only — it is
never hardcoded.

**Signals.** The Disruption Sensing Agent pulls headlines from `SIGNAL_FEEDS` (default:
Google News RSS queries on supply-chain disruptions). If every feed is unreachable it
falls back to a built-in offline sample, so demos never come back empty.

## Tests

```bash
cd backend
pytest -q
```

CI runs the same suite on every push and pull request (see `.github/workflows/ci.yml`).

## Docker

```bash
docker build -f backend/Dockerfile -t chainguard-ai .
docker run -p 8000:8000 chainguard-ai
```

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Service banner. |
| GET | `/health` | Health check. |
| GET | `/api/dashboard` | Counts plus recent disruptions and approvals. |
| GET | `/api/signals` | Fetch and classify live external signals. |
| POST | `/api/disruptions` | Create a disruption record. |
| GET | `/api/disruptions` | List disruptions (`limit`, `offset`). |
| POST | `/api/analyze` | Run the agent pipeline for a scenario. |
| GET | `/api/analyses/{id}` | Fetch a stored analysis. |
| GET | `/api/approvals` | List approval requests (`limit`, `offset`). |
| POST | `/api/approvals/{id}/decision` | Approve or reject a request. |
| GET | `/api/audit` | Read the audit log (`limit`, `offset`). |
| POST | `/api/inventory/rebalance` | Inventory recommendation only. |

List endpoints accept `limit` (1–500, default 50) and `offset` (default 0) and return
`{ items, total, limit, offset }`.

## Quick example

```bash
# 0. See live disruption signals
curl http://127.0.0.1:8000/api/signals?limit=5

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
├── .dockerignore
├── .gitignore
├── .github/workflows/ci.yml
├── README.md
└── backend
    ├── main.py             # FastAPI app and routes
    ├── agents.py           # agent pipeline + classification
    ├── signals.py          # RSS/Atom ingestion
    ├── llm.py              # provider-agnostic LLM client
    ├── models.py           # Pydantic request models
    ├── database.py         # SQLite helpers
    ├── conftest.py         # test fixtures
    ├── tests/              # test suite
    ├── static/index.html   # demo dashboard
    ├── requirements.txt
    ├── requirements-dev.txt
    ├── Dockerfile
    └── .env.example
```

## Notes

- The SQLite database (`chainguard.db`) is created on first run and is **not**
  committed to git.
- `.env` holds local config and is git-ignored; only `.env.example` is tracked.
- No credentials are ever hardcoded; all secrets come from the environment.
