# ══════════════════════════════════════════════════════════════════════════════
#  Stage 1 — Builder
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ══════════════════════════════════════════════════════════════════════════════
#  Stage 2 — Runtime
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS runtime

WORKDIR /app

ARG APP_PORT=8000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    APP_PORT=${APP_PORT} \
    APP_WORKERS=1

COPY --from=builder /install /usr/local

# App source + migrations + scripts (alembic runs from CI, scripts run from cron)
COPY src/          ./src/
COPY migrations/   ./migrations/
COPY scripts/      ./scripts/
COPY alembic.ini   .
COPY pyproject.toml .

RUN pip install --no-cache-dir --no-deps .

RUN mkdir -p /app/logs

RUN adduser --disabled-password --gecos "" appuser
RUN chown appuser:appuser /app/logs
USER appuser

EXPOSE ${APP_PORT}

# Default = API. Override at runtime for worker / cron job:
#   worker:    taskiq worker app.core.config.broker:broker app.background.tasks
#   cron job:  python scripts/trigger_monthly_review.py
CMD ["sh", "-c", "exec fastapi run src/app/main.py --port ${APP_PORT} --workers ${APP_WORKERS}"]
