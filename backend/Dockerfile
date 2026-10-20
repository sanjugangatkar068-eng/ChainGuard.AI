# The build context for this image is the backend/ directory — the folder this file
# lives in — so every COPY path below is relative to backend/.
#
#   docker build -t chainguard-ai backend/
#   docker run -p 8000:8000 -e API_KEY=change-me chainguard-ai
#
# On a platform with a "Root Directory" setting (e.g. Render), set it to `backend` and
# the Dockerfile path to `Dockerfile` — the context then matches these paths.
#
# If you ever build with the REPOSITORY ROOT as the context instead, prefix each COPY
# path with `backend/` or you will get:  failed to compute cache key: "/backend": not found
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Honour $PORT when the platform injects one; fall back to 8000 for local runs.
# "exec" keeps uvicorn as PID 1 so it receives shutdown signals.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
