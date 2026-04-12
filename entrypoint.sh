#!/bin/sh
set -e

echo "[entrypoint] Running database migrations..."
alembic upgrade head
echo "[entrypoint] Migrations done."

echo "[entrypoint] Starting app on port ${APP_PORT:-8000} with ${APP_WORKERS:-1} worker(s)..."
exec fastapi run src/app/main.py \
    --port  "${APP_PORT:-8000}"  \
    --workers "${APP_WORKERS:-1}"
