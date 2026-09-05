#!/usr/bin/env bash
set -e

echo "Starting Repo Intel backend services..."

# Start Celery worker in background
celery -A app.worker.celery_app worker --loglevel=info --concurrency=2 &
CELERY_PID=$!

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 2 &
UVICORN_PID=$!

# Trap signals for graceful termination
trap "kill -TERM $CELERY_PID $UVICORN_PID" SIGTERM SIGINT

# Wait for processes
wait $UVICORN_PID $CELERY_PID
