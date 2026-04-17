#!/bin/sh
set -eu

export PORT="${PORT:-10000}"
export HOSTNAME="0.0.0.0"
export DATABASE_URL="${DATABASE_URL:-sqlite:////app/data/rideguard.db}"
export SECRET_KEY="${SECRET_KEY:-rideguard-render-secret}"
export TOKEN_ISSUER="${TOKEN_ISSUER:-rideguard-api}"
export ACCESS_TOKEN_EXPIRE_MINUTES="${ACCESS_TOKEN_EXPIRE_MINUTES:-480}"
export ENABLE_TRIGGER_MONITOR="${ENABLE_TRIGGER_MONITOR:-false}"
export CORS_ORIGINS="${CORS_ORIGINS:-${RENDER_EXTERNAL_URL:-http://127.0.0.1:${PORT}}}"

# Configure Celery for eager (in-process) execution on Render where no Redis exists
export CELERY_TASK_ALWAYS_EAGER="${CELERY_TASK_ALWAYS_EAGER:-true}"
export CELERY_BROKER_URL="${CELERY_BROKER_URL:-memory://}"
export CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-cache+memory://}"

cd /app/backend
/opt/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/ >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

cd /app/frontend/.next/standalone
exec node server.js
