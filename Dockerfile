# ══════════════════════════════════════════════════════════════════════════════
#  Stage 1 — Builder
#  Install + compile all dependencies (including C extensions).
#  Result: /install  (copied into the runtime stage, no build tools needed)
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS builder

WORKDIR /build

# Build-time deps for C extensions (asyncpg, argon2-cffi, bcrypt…)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ══════════════════════════════════════════════════════════════════════════════
#  Stage 2 — Runtime
#  Lean image: no compiler, no build cache, only what the app needs.
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# Copy compiled packages from builder
COPY --from=builder /install /usr/local

# App source & migration files (alembic needs them at runtime)
COPY src/          ./src/
COPY migrations/   ./migrations/
COPY alembic.ini   .
COPY pyproject.toml .

# Install the app package itself (no deps, already in /usr/local above)
RUN pip install --no-cache-dir --no-deps .

# Entrypoint: runs migrations then starts the app (reads APP_PORT / APP_WORKERS from env)
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Run as non-root for security
RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
