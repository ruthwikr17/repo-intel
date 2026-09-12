#!/usr/bin/env bash
set -e

echo "Starting Repo Intel API..."

# This command is for the Render *web service* only.  Keep the Celery worker
# in a separate Render Background Worker using start-worker.sh; otherwise a
# web-service restart kills in-flight analyses and makes status polling fail.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WEB_CONCURRENCY:-1}"
