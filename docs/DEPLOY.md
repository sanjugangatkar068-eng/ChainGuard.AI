# Deploying ChainGuard AI

The project ships two deployable pieces: the **FastAPI backend** and the **React
frontend**. You can run them together locally, or host them separately.

> **Set `API_KEY` before exposing anything publicly.** Auth is opt-in: with `API_KEY`
> unset, every mutating endpoint is open to anyone who finds the URL. See
> [`../SECURITY.md`](../SECURITY.md).

---

## 1. Docker (local, quickest check)

The build context is the **`backend/`** directory — the Dockerfile's COPY paths are
relative to it:

```bash
docker build -t chainguard-ai backend/
docker run -p 8000:8000 -e API_KEY=change-me chainguard-ai
```

Then open <http://127.0.0.1:8000/docs>.

**Why the context matters.** `COPY requirements.txt .` resolves inside the context, so
if the context is the *repository root* instead of `backend/`, the build fails with:

```
failed to compute cache key: "/backend": not found
```

Rule of thumb: **the context and the Dockerfile must agree.** Either
context = `backend/` with the committed Dockerfile (recommended), or context = repo root
with a Dockerfile whose paths are prefixed `backend/`. Mixing the two produces exactly
the error above.

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

| Setting | Value |
| --- | --- |
| Root directory | `backend` |
| Dockerfile path | `Dockerfile` |
| Docker context | the root directory (`backend`) |

The Dockerfile's COPY paths are relative to `backend/`, so the context must be that
folder — which is what setting Root Directory to `backend` gives you. The image reads
`$PORT` if the platform provides one, and otherwise listens on 8000.

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
| `failed to compute cache key: "/backend": not found` | The context and Dockerfile disagree. Set Root Directory = `backend` (context `backend/`, Dockerfile `Dockerfile`), or use the repo root as context with Dockerfile `backend/Dockerfile`. |
| `502` / `Connection refused` | The app isn't bound to `0.0.0.0` or isn't using `$PORT`. |
| UI loads but every action fails | `CORS_ORIGINS` on the backend doesn't include the frontend origin. |
| `401 Invalid or missing API key` | `API_KEY` is set on the backend but `VITE_API_KEY` isn't set on the frontend (or they differ). |
| Dashboard empty after deploy | Expected — the database is fresh. Run `python seed.py --reset` locally, or create data through the UI. |
| First load very slow | Free-tier cold start. Subsequent requests are fast. |
