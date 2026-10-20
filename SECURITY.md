# Security

ChainGuard AI is a demonstration system. It is built to be **safe by default** —
it never executes a supply-chain action, and it runs without credentials — but it is
not hardened for untrusted public exposure out of the box. This document states
plainly what is protected, what is not, and how to report a problem.

## Threat model

The system ingests **untrusted external text** (RSS/Atom headlines) and stores it. It
is expected to run either locally, inside a container, or behind a private network.
The assets worth protecting are: the SQLite database, any configured secrets
(`API_KEY`, `LLM_API_KEY`, `ALERT_WEBHOOK_URL`), and the integrity of the audit trail.

## Controls in place

| Area | Control |
| --- | --- |
| **Authentication** | Optional API-key auth on all mutating endpoints. Set `API_KEY` and every `POST` requires a matching `X-API-Key` header. Comparison uses `secrets.compare_digest` (timing-safe). |
| **Input validation** | All request bodies are validated by Pydantic with explicit type, length and range bounds (e.g. `delay_days` 0–90, `title` 3–160 chars, `description` ≤ 2000 chars). |
| **SQL injection** | All values are passed as bound parameters. Table/column names are internal constants, never user input. |
| **CSV / formula injection** | Exported CSV cells beginning with `= + - @` (tab/CR) are prefixed with an apostrophe, so a malicious headline cannot execute as a spreadsheet formula (OWASP CSV injection). |
| **XSS** | The React frontend relies on JSX auto-escaping; the static dashboard escapes every interpolated value. No `dangerouslySetInnerHTML`. |
| **Secrets** | No credentials are hardcoded. `.env` is git-ignored; only `.env.example` with placeholders is tracked. Secrets are read from the environment. |
| **SSRF** | The only outbound calls are to operator-configured URLs (`ALERT_WEBHOOK_URL`, `SIGNAL_FEEDS`). They are not settable by an API caller. |
| **Error handling** | Endpoints return generic `detail` messages; stack traces are not exposed to clients. A failing role is recorded internally and never surfaced as a 500. |
| **Audit** | Every state change writes an audit event with actor and details. |
| **Dependency updates** | Dependabot is configured for pip, npm and GitHub Actions. |
| **No autonomous side effects** | Every output is a recommendation. The system never books, orders or reroutes anything. |

## Known limitations (not addressed)

Be aware of these before exposing the service:

1. **Auth is opt-in.** With `API_KEY` unset — the default — **the API is fully open**.
   Anyone who can reach it can create disruptions, approve recommendations and run
   autonomous cycles. Set `API_KEY` for anything beyond local use.
2. **No rate limiting.** There is no protection against request flooding or abuse of
   the `/api/orchestrator/cycle` endpoint.
3. **SQLite is single-file and unencrypted.** Anyone with filesystem access can read
   or edit the database, including the audit trail.
4. **Prompt injection (LLM mode).** When `LLM_PROVIDER` is set, untrusted headline text
   is passed to the model. The system prompt instructs it not to invent data, but a
   crafted headline could still influence the generated explanation. The LLM output is
   narrative only — it does not change the deterministic recommendation.
5. **No CSRF protection.** With auth disabled and permissive CORS, a browser-based
   caller is not protected against cross-site requests.
6. **Audit log is not tamper-evident.** It is an append-only table, not a hash-chained
   or signed ledger, so a database write could alter history (compare with projects
   such as AGRI-BRAIN and PharmaDT, which use Merkle-anchored ledgers).
7. **No PII handling policy.** Do not put personal data into disruption descriptions.

## Recommended for a public deployment

- Set `API_KEY` (and serve over HTTPS).
- Put the service behind a reverse proxy with rate limiting and a request body size cap.
- Restrict `CORS_ORIGINS` to the exact frontend origin.
- Mount the database on encrypted, access-controlled storage, or move to a managed
  database with backups.
- Keep dependencies current (Dependabot PRs) and run the test suite in CI.

## Reporting a vulnerability

Please **do not** open a public issue for a security problem. Report it privately to
the repository owner (see the GitHub profile on the repository page), including
reproduction steps and impact. There is no formal SLA — this is a student project —
but reports will be acknowledged and addressed as promptly as possible.
