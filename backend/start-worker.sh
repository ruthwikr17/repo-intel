#!/usr/bin/env bash
set -euo pipefail

echo "Starting Repo Intel Celery worker..."

# This command is for a Render Background Worker.  Do not run it from the
# web-service start command: web deploys and restarts must not interrupt jobs.
exec celery -A app.worker.celery_app worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-2}"
