# Build from the REPOSITORY ROOT — the folder that contains backend/ and frontend/.
#
#   docker build -f backend/Dockerfile -t chainguard-ai .
#   docker run -p 8000:8000 chainguard-ai
#
# The build context MUST be the repo root: every COPY path below is relative to it.
# Building from inside backend/ fails with:  "/backend": not found
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 8000

# Honour $PORT when the platform injects one; fall back to 8000 for local runs.
# "exec" keeps uvicorn as PID 1 so it receives shutdown signals.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
