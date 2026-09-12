#!/usr/bin/env bash
set -euo pipefail

echo "Starting Repo Intel API and Celery worker..."

# Render's Free instance has 512 MB RAM.  The previous configuration created
# two Uvicorn processes and two Celery prefork children, which can exhaust that
# limit and restart the service while an analysis is being polled.  Keep one
# non-forking worker in this same service instead.
celery -A app.worker.celery_app worker \
  --loglevel=info \
  --pool=solo \
  --concurrency="${CELERY_CONCURRENCY:-1}" &
CELERY_PID=$!

uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-1}" &
UVICORN_PID=$!

shutdown() {
  echo "Stopping Repo Intel services..."
  kill -TERM "$CELERY_PID" "$UVICORN_PID" 2>/dev/null || true
  wait "$CELERY_PID" 2>/dev/null || true
  wait "$UVICORN_PID" 2>/dev/null || true
  exit "${1:-0}"
}

trap shutdown SIGTERM SIGINT

# If either process crashes, stop the other process and let Render restart this
# service.  With late acknowledgements and reject-on-worker-lost configured in
# app.worker, Redis makes any in-flight analysis available to the next worker.
if wait -n "$CELERY_PID" "$UVICORN_PID"; then
  EXIT_CODE=0
else
  EXIT_CODE=$?
fi
shutdown "$EXIT_CODE"
