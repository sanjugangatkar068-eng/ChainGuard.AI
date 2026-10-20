# Theme Alignment & Related Work

This document maps ChainGuard AI against the **Resilient Supply Chains** hackathon theme
and positions it against other open-source projects in the same space.

---

## 1. Theme coverage

The theme describes a solution that "decomposes into collaborating agents with clear
roles and human handoffs." Here is how each described role maps to what this repository
actually implements.

| Theme role | What ChainGuard AI implements | Where |
| --- | --- | --- |
| **Disruption Sensing Agent** — monitors maritime alerts, weather, tariffs, port congestion and news; classifies events by severity; escalates ambiguous signals | Ingests RSS/Atom feeds (default: Google News queries on supply-chain disruptions), classifies each headline into a disruption type by keyword, and scores severity into a risk level with a confidence value and a source label | `backend/signals.py`, `backend/agents.py` (`classify_signal`, `signal_ingestion_agent`, `disruption_sensing`), `GET /api/signals` |
| **Scenario Planning Agent** — runs "what if" scenarios (Suez closes, tariffs hit 50%, supplier goes offline) and evaluates cost, time and risk | Builds three response options (wait / reroute / expedite), each with estimated extra cost, delay and risk, checked against a configurable budget | `agents.scenario_planning` |
| **Rerouting & Logistics Agent** — adjusts routes, rebalances freight, updates timelines | Turns the recommended scenario into an action, a route label and a revised ETA | `agents.logistics_agent` |
| **Inventory Rebalancing Agent** — recalculates safety stock, reallocates inventory within budget and policy guardrails | Recomputes reorder point, projected stock and replenishment units with a cost estimate | `agents.inventory_agent` |
| **Compliance & Audit Agent** — logs every decision with rationale and sources, ensures regulatory compliance, generates audit reports | Flags high-risk cases and budget breaches, produces a compliance report, writes every event to an audit log, and exposes CSV exports | `agents.compliance_agent`, `audit_logs` table, `GET /api/audit`, `GET /api/export/analyses.csv` |
| **Human-in-the-loop** — pauses on high-stakes calls and presents options with context | Creates an approval record for high-risk assessments; a reviewer approves or rejects; an Escalation Agent raises an alert at a configurable threshold | `approvals` table, `POST /api/approvals/{id}/decision`, `agents.escalation_agent`, `backend/alerting.py` |

### Additional agents beyond the theme

| Agent | Purpose |
| --- | --- |
| **Supplier Risk Agent** | Scores a supplier network for exposure and flags sourcing concentration (multi-tier visibility). |
| **Explanation Agent** | Produces a plain-language rationale — via an LLM if configured, otherwise a deterministic template. |

### Where this implementation deliberately differs

Being honest about the gaps matters more than claiming full coverage:

- **"Executes the chosen response."** The theme's Rerouting agent "executes"; ChainGuard
  AI is **recommendation-only by design** — it never books, orders or reroutes anything.
  Every output carries `execution_status: "recommendation_only"`. This is a deliberate
  safety choice, not a missing feature.
- **"Escalating ambiguous signals."** Signal classification is **keyword-based**, not
  LLM-based ambiguity detection. Confidence is a simple heuristic (based on how many
  fields are populated), not a calibrated probability.
- **Data sources.** Only RSS news feeds are wired up. Live maritime, weather and tariff
  APIs are not integrated — the architecture allows it (see `SIGNAL_FEEDS`), but each
  needs its own API key and adapter.
- **Risk scoring.** Supplier and disruption scores are transparent, illustrative
  heuristics — useful for a demo and easy to defend, but not validated models.

---

## 2. Related projects

Other open-source efforts on the same problem. Most are hackathon or portfolio projects
(often with few or no stars), and the descriptions are as reported by their own READMEs.

| Project | Approach | How ChainGuard AI differs |
| --- | --- | --- |
| [DisruptOps](https://github.com/Suhaibkhanmn/event-driven-supply-chain-disruption-response-agent) | Agentic RAG pipeline (Watcher → Extractor → Matcher → Planner → Executor) using Gemini; RSS monitoring; human-in-the-loop approvals; email execution | ChainGuard runs **without any LLM or API key** by default, and is recommendation-only (no email execution) |
| [SupplySentinel](https://github.com/G26karthik/SupplySentinel) | Multi-agent risk monitor (Config / Watchman / Analyst / Dispatcher) on Gemini, deployed on Google Cloud Run | ChainGuard ships a deterministic, testable pipeline plus an optional LLM layer, rather than LLM-only agents |
| [marga](https://github.com/this-isnt-daniel/marga) | Autonomous disruption agent; four separate FastAPI services (mock ERP, freight, booking, approval) + dashboard | ChainGuard is a **single service** with one datastore; both share the human-approval pattern |
| [Supply Chain Agent](https://github.com/dhanush-r-m/Supply-Chain-Agent) | Next.js + LangGraph + Gemini + Supabase + Pinecone; Monitor → Risk → Supplier Discovery → Decision → Execution → Notification → Memory | ChainGuard keeps state in SQLite and avoids vector stores and external LLM dependencies |
| [proactive-supply-chain-disruption-agent](https://github.com/Smit-Parekh/proactive-supply-chain-disruption-agent) | Fine-tuned Gemma-3 (PEFT/LoRA) + LangGraph, Vertex AI + MLflow MLOps | ChainGuard targets a lightweight, fully local demo rather than a trained-model MLOps pipeline |
| [Supply Chain Risk Intelligence](https://github.com/aniket-work/supply-chain-risk-intelligence) | Four LangGraph agents (Market Analyst → Logistics Coordinator → Inventory Strategist → Executive Orchestrator) | Same agent decomposition, but ChainGuard adds persistent audit, approvals and CSV reporting |
| [agentic-supply-chain-operations-platform](https://github.com/Aprameya-C-V/agentic-supply-chain-operations-platform) | LangGraph + Deep Agents + FastAPI + React + MLflow + ClickHouse | ChainGuard uses the same FastAPI + React shape with far fewer moving parts |
| [Agentic ERP Supply Chain Copilot](https://github.com/mnguegnang/Agentic-ERP-end-to-end-development) | LangGraph orchestrator + 7 OR-Tools/CVXPY/SciPy solvers, Neo4j, CRAG retrieval, HITL approval gate, AKS deploy | ChainGuard is solver-free and deterministic; the other project is optimisation-heavy |
| [chAIn](https://github.com/khuynh22/chAIn) | Multi-agent "council" with NVIDIA Cosmos world models on AWS SageMaker, MCP tool servers | ChainGuard has no GPU/model-serving dependency |
| [InvAgent](https://github.com/zefang-liu/InvAgent) | Research: LLM-based multi-agent inventory management (zero-shot), with IPPO/MAPPO baselines | ChainGuard is an applied product slice, not a research environment |
| [AGRI-BRAIN](https://github.com/kprodigi/AGRI-BRAIN) | Physics-informed multi-agent framework with MCP tooling and a Merkle-anchored audit ledger | Both emphasise auditable decisions; ChainGuard uses a simple append-only log rather than a hash-chained ledger |
| [PharmaDT](https://github.com/Sandy-383/PharmaDT) | Digital twin + five agents + cryptographic provenance ledger + federated learning, FastAPI + React | ChainGuard is smaller in scope but shares the FastAPI + React + audit-trail structure |
| [SupplyChainAgenticAI](https://github.com/cinapr/SupplyChainAgenticAI) | LangChain + Ollama (local LLM, no API key) for a food supply chain | Both run fully locally with no API key — a rare point of agreement |

### The common shape

Across these projects, a recurring architecture emerges that ChainGuard AI follows:

```
sensing / monitoring  →  risk assessment  →  planning  →  human approval  →  audit
```

Differences cluster in four places: **(a)** whether an LLM is required, **(b)** whether
the system merely recommends or actually executes, **(c)** how state and audit are
persisted, and **(d)** how heavy the infrastructure is. ChainGuard AI sits at the light,
deterministic, recommendation-only end of that space — which is what makes it runnable
and testable without credentials.

---

## 3. References

- **SAP HackFest 2026 — Resilient Supply Chains theme** (the source of the agent roles
  quoted above): <https://events.sap.com/in-hackfest-2026/en_us/home.html>
- The theme cites these industry sources for its problem framing: IDC (skills gap),
  World Economic Forum (Future of Jobs / reskilling), PwC (AI wage premium), and the
  India Skills Report. These figures are **as stated by the theme page**, not
  independently verified here.
- Project links are listed inline in the table above.

> Note: third-party project descriptions are summarised from their public READMEs and
> were not independently tested. Treat them as claims, not verified facts.
