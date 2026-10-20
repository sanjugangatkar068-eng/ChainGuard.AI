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
| Disruption Sensing Agent | Ingests RSS/Atom feeds, classifies headlines, and scores severity with a confidence and source. |
| Scenario Planning Agent | Compares wait / reroute / expedite options on cost and delay, within budget. |
| Rerouting & Logistics Agent | Turns the chosen scenario into a route, revised ETA and cost. |
| Inventory Rebalancing Agent | Recomputes reorder point and replenishment needs. |
| Supplier Risk Agent | Scores suppliers by exposure and flags sourcing concentration (multi-tier visibility). |
| Compliance & Audit Agent | Flags high-risk cases and budget breaches; produces a compliance report. |
| Escalation Agent | Raises an alert when risk meets the configured threshold and review is required. |
| Explanation Agent | Narrates the assessment in plain language (LLM if configured, else rules). |
| Human-in-the-loop | A reviewer approves or rejects high-risk recommendations. |

See [`docs/REFERENCES.md`](docs/REFERENCES.md) for how these map to the hackathon
theme's agent roles, an honest note on where this implementation differs, and a
comparison with related open-source projects.

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
- Built-in demo dashboard (no build step): http://127.0.0.1:8000/dashboard

## Frontend (React)

A Vite + React single-page app lives in `frontend/`. It talks to the API over HTTP and
covers the whole flow: report a disruption, run the agent pipeline, review the
per-agent output (with charts), approve/reject, acknowledge alerts and read the audit
trail.

```bash
cd frontend
npm install
cp .env.example .env        # optional: set VITE_API_URL
npm run dev                 # http://localhost:5173
```

Start the backend first (port 8000). The frontend reads its API base URL from
`VITE_API_URL` (default `http://127.0.0.1:8000`), and the backend allows the Vite origin
via `CORS_ORIGINS` in `backend/.env`. Production build: `npm run build` (output in
`frontend/dist`).

> There is also a dependency-free static dashboard served by the backend at
> `/dashboard` — handy if Node isn't installed or you want a guaranteed-offline demo.

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
| `ALERT_MIN_LEVEL` | Risk level at which to escalate (`low`/`medium`/`high`/`critical`, default `high`). |
| `ALERT_WEBHOOK_URL` | Optional webhook to POST alerts to; if empty, alerts are recorded with channel `log`. |

**LLM reasoning is optional.** With `LLM_PROVIDER=none` (or no key), the Explanation
Agent uses a deterministic template, so the app always works. Set a provider and key
to get natural-language rationales. The key is read from the environment only — it is
never hardcoded.

**Signals.** The Disruption Sensing Agent pulls headlines from `SIGNAL_FEEDS` (default:
Google News RSS queries on supply-chain disruptions). If every feed is unreachable it
falls back to a built-in offline sample, so demos never come back empty.

**Alerts.** When a disruption's risk level meets `ALERT_MIN_LEVEL` and human review is
required, the Escalation Agent raises an alert. Alerts are always recorded; they are
also POSTed as JSON to `ALERT_WEBHOOK_URL` if one is set. Delivery is best-effort and
never breaks the request. Alerts are acknowledgement-tracked via `/api/alerts`.

## Code quality

- **Ruff** config lives in `pyproject.toml` (also holds the pytest options). Run
  `ruff check backend`.
- **Pre-commit** hooks (`.pre-commit-config.yaml`) run Ruff and basic hygiene checks.
  Enable once with `pre-commit install`; refresh versions with `pre-commit autoupdate`.
- A **Makefile** offers `make install`, `make run`, `make test`, `make seed`, `make lint`
  and `make clean` (use Git Bash or WSL on Windows).

## VS Code

Open the repository folder in VS Code and you get, out of the box:

- **Run & Debug** → *ChainGuard API (uvicorn)* launches the backend with the debugger
  attached; *Frontend: Chrome* opens the UI with a browser debugger; *Pytest (current
  file)* debugs a single test.
- **Terminal → Run Task** → install/run/test for both backend and frontend, seed demo
  data, or **Full stack: backend + frontend** to start both servers at once.
- **Testing** sidebar discovers the pytest suite; the Vitest extension discovers the
  frontend tests.
- Recommended extensions (Python, Pylance, debugpy, Ruff, Vitest) are suggested on open.

A **Dev Container** is included (`.devcontainer/`): open the folder with
*Dev Containers: Reopen in Container* (or a GitHub Codespace) to get Python 3.12 **and
Node 20** with both dependency sets installed, and ports 8000 and 5173 forwarded.

## Demo data

Populate the database with sample disruptions, analyses and approvals so a demo
starts with content:

```bash
cd backend
python seed.py            # add demo data
python seed.py --reset    # clear tables first
```

The dashboard then opens with data already in it. The seed runs the full agent
pipeline (including the Supplier Risk agent) on each demo disruption.

## Tests

Backend:

```bash
cd backend
pytest -q
```

Frontend (Vitest + Testing Library):

```bash
cd frontend
npm test          # single run
npm run test:watch
```

CI runs both suites on every push and pull request (see `.github/workflows/ci.yml`).

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
| GET | `/api/alerts` | List escalation alerts (`limit`, `offset`). |
| POST | `/api/alerts/{id}/ack` | Acknowledge an alert. |
| GET | `/api/export/analyses.csv` | Download all analyses as a CSV report. |
| GET | `/api/export/audit.csv` | Download the audit trail as a CSV report. |
| POST | `/api/suppliers/risk` | Score a supplier network for exposure and concentration. |
| POST | `/api/inventory/rebalance` | Inventory recommendation only. |

List endpoints accept `limit` (1–500, default 50) and `offset` (default 0) and return
`{ items, total, limit, offset }`.

`POST /api/analyze` accepts an optional `suppliers` array (each: `name`, `tier`,
`country`, `single_source`, `lead_time_days`, `spend_usd`). When present, the response
includes a `supplier_risk` block from the Supplier Risk agent.

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
├── .devcontainer           # VS Code Dev Container / Codespaces
│   └── devcontainer.json
├── .dockerignore
├── .editorconfig
├── .gitignore
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml
├── .vscode                 # shared debug, task and extension config
│   ├── extensions.json
│   ├── launch.json
│   ├── settings.json
│   └── tasks.json
├── LICENSE
├── Makefile                # install / run / test / seed shortcuts
├── README.md
├── pyproject.toml          # ruff + pytest configuration
├── docs
│   ├── ARCHITECTURE.md     # component map, data flow, data model
│   └── REFERENCES.md       # theme alignment + related projects
├── backend
    ├── main.py             # FastAPI app and routes
    ├── agents.py           # agent pipeline + classification
    ├── signals.py          # RSS/Atom ingestion
    ├── llm.py              # provider-agnostic LLM client
    ├── models.py           # Pydantic request models
    ├── database.py         # SQLite helpers
    ├── seed.py             # demo-data seeder
    ├── conftest.py         # test fixtures
    ├── tests/              # test suite
    ├── static/index.html   # demo dashboard (charts, no build step)
    ├── requirements.txt
    ├── requirements-dev.txt
    ├── Dockerfile
    └── .env.example
└── frontend
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── .env.example
    └── src
        ├── main.jsx
        ├── App.jsx
        ├── api.js
        ├── styles.css
        └── components/     # StatCards, DisruptionForm, PipelineResult, ...
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the component map and data flow,
and [`docs/REFERENCES.md`](docs/REFERENCES.md) for theme alignment and related work.

## Notes

- The SQLite database (`chainguard.db`) is created on first run and is **not**
  committed to git.
- `.env` holds local config and is git-ignored; only `.env.example` is tracked.
- No credentials are ever hardcoded; all secrets come from the environment.
- Released under the MIT License (see `LICENSE`).
