# Deploying ChainGuard AI

The project ships two deployable pieces: the **FastAPI backend** and the **React
frontend**. You can run them together locally, or host them separately.

> **Set `API_KEY` before exposing anything publicly.** Auth is opt-in: with `API_KEY`
> unset, every mutating endpoint is open to anyone who finds the URL. See
> [`../SECURITY.md`](../SECURITY.md).

---

## 1. Docker (local, quickest check)

Run from the **repository root**, not from `backend/`:

```bash
cd /path/to/ChainGuard.AI        # repo root
docker build -f backend/Dockerfile -t chainguard-ai .
docker run -p 8000:8000 -e API_KEY=change-me chainguard-ai
```

Then open <http://127.0.0.1:8000/docs>.

**Why the context matters:** the Dockerfile starts with `COPY backend/requirements.txt .`,
and COPY paths are relative to the build context. Building from inside `backend/` gives:

```
failed to compute cache key: "/backend": not found
```

The context must be the repo root. In a cloud builder, set **Dockerfile Path =
`backend/Dockerfile`** and **Docker Context = `.`**.

---

## 2. Backend as a native Python service (e.g. Render)

| Setting | Value |
| --- | --- |
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |

Environment variables:

| Variable | Value |
| --- | --- |
| `API_KEY` | a long random string (required for public use) |
| `CORS_ORIGINS` | your frontend origin, e.g. `https://your-app.onrender.com` |
| `DATABASE_PATH` | `chainguard.db`, or a path on a mounted disk (see caveats) |
| `ORCHESTRATOR_INTERVAL_SECONDS` | `0` to disable the background loop, or e.g. `300` |

## 3. Backend as a Docker service

Same as above, but:

| Setting | Value |
| --- | --- |
| Dockerfile path | `backend/Dockerfile` |
| Docker context | `.` (repo root) |

The image reads `$PORT` if the platform provides one, and otherwise listens on 8000.

## 4. Frontend as a static site (e.g. Render Static Site, Netlify, Vercel, Pages)

| Setting | Value |
| --- | --- |
| Root directory | `frontend` |
| Build command | `npm ci && npm run build` |
| Publish directory | `frontend/dist` (or `dist` if root is `frontend`) |

Environment variables (these are baked in **at build time**):

| Variable | Value |
| --- | --- |
| `VITE_API_URL` | your backend URL, e.g. `https://chainguard-api.onrender.com` |
| `VITE_API_KEY` | the same value as the backend's `API_KEY` |

---

## Order of operations

1. Deploy the **backend** first and note its URL.
2. Deploy the **frontend** with `VITE_API_URL` pointing at that backend URL.
3. Go back and set the backend's `CORS_ORIGINS` to the frontend's URL, then redeploy
   the backend.

Skipping step 3 is the most common cause of a blank UI with CORS errors in the console.

---

## Caveats

- **SQLite is ephemeral on most platforms.** The filesystem is reset on redeploy, so
  seeded data disappears. For persistence, attach a disk and point `DATABASE_PATH` at
  it, or migrate to a managed Postgres.
- **`VITE_API_URL` and `VITE_API_KEY` are inlined at build time.** Changing either
  requires a frontend rebuild — they are not read at runtime.
- **Free tiers sleep.** The first request after idle can take 30–60 seconds.
- **The autonomous loop only runs while the process is up.** On a host that sleeps the
  instance, scheduled cycles pause with it.
- **Signals need outbound network access.** If the host blocks egress, the Disruption
  Sensing Agent falls back to the built-in offline sample (by design).

---

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `failed to compute cache key: "/backend": not found` | Build context is `backend/`. Use the repo root (see §1). |
| `502` / `Connection refused` | The app isn't bound to `0.0.0.0` or isn't using `$PORT`. |
| UI loads but every action fails | `CORS_ORIGINS` on the backend doesn't include the frontend origin. |
| `401 Invalid or missing API key` | `API_KEY` is set on the backend but `VITE_API_KEY` isn't set on the frontend (or they differ). |
| Dashboard empty after deploy | Expected — the database is fresh. Run `python seed.py --reset` locally, or create data through the UI. |
| First load very slow | Free-tier cold start. Subsequent requests are fast. |
