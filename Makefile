# ══════════════════════════════════════════════════════════════════════════════
#  Nyaya — Developer Makefile
#  Compatible: Linux / macOS / Windows (Git Bash)
# ══════════════════════════════════════════════════════════════════════════════

# ── Docker compose shortcuts ──────────────────────────────────────────────────

APP_ENTRY := src/app/main.py
DC_BASE   := docker compose -f infrastructure/docker-compose.base.yml --env-file .env
DC_DEV    := $(DC_BASE) -f infrastructure/docker-compose.dev.yml
DC_PROD   := $(DC_BASE) -f infrastructure/docker-compose.prod.yml

# ── Venv ──────────────────────────────────────────────────────────────────────
# Each Make recipe runs in its own shell so `source .venv/bin/activate` doesn't
# persist. Pointing directly to the venv binaries is exactly equivalent.

ifeq ($(OS),Windows_NT)
  VENV_BIN      := .venv/Scripts
  PYTHON_SYSTEM := py
else
  VENV_BIN      := .venv/bin
  PYTHON_SYSTEM := python3
endif

PYTHON      := $(VENV_BIN)/python
PIP         := $(VENV_BIN)/pip
PIP_SYNC    := $(VENV_BIN)/pip-sync
PIP_COMPILE := $(VENV_BIN)/pip-compile
FASTAPI     := $(VENV_BIN)/fastapi
ALEMBIC     := $(VENV_BIN)/alembic
PYTEST      := $(VENV_BIN)/pytest

.PHONY: _venv-check
_venv-check:
	@test -f $(PYTHON) \
		|| (echo "" \
		&&  echo "  ERROR: virtual environment not found." \
		&&  echo "  Run:   make setup" \
		&&  echo "" \
		&&  exit 1)

# ── Default ───────────────────────────────────────────────────────────────────

.DEFAULT_GOAL := help

# ══════════════════════════════════════════════════════════════════════════════
#  HELP
# ══════════════════════════════════════════════════════════════════════════════

.PHONY: help
help: ## Show available commands
	@echo ""
	@echo "  Nyaya — available commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ══════════════════════════════════════════════════════════════════════════════
#  SETUP  (first-time only)
# ══════════════════════════════════════════════════════════════════════════════

.PHONY: venv
venv: ## Create the virtual environment (.venv)
	$(PYTHON_SYSTEM) -m venv .venv

.PHONY: install
install: _venv-check ## Install dependencies for the first time (before pip-sync is available)
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .

.PHONY: setup
setup: venv install sync ## First-time setup: venv → install → services → migrate
	@echo ""
	@echo "  Setup complete. Run 'make dev'."
	@echo ""

# ══════════════════════════════════════════════════════════════════════════════
#  DEV
# ══════════════════════════════════════════════════════════════════════════════

.PHONY: up
up: ## Start dev services (Postgres + Redis)
	$(DC_DEV) up -d
	@echo "Waiting for Postgres..."
	@until $(DC_DEV) exec -T postgres pg_isready -q 2>/dev/null; do printf "."; sleep 1; done
	@echo " ready."

.PHONY: sync
sync: _venv-check up ## Recompile deps + sync venv + apply migrations — run after every git pull
	$(PIP_COMPILE) requirements.in     -o requirements.txt
	$(PIP_COMPILE) requirements-dev.in -o requirements-dev.txt
	$(PIP_SYNC) requirements-dev.txt
	$(PIP) install --no-deps -e .
	$(ALEMBIC) upgrade head

.PHONY: dev
dev: _venv-check up ## Start FastAPI dev server with hot reload
	$(FASTAPI) dev $(APP_ENTRY)

.PHONY: down
down: ## Stop dev services
	$(DC_DEV) down

.PHONY: logs
logs: ## Follow dev services logs (Ctrl+C to stop)
	$(DC_DEV) logs -f

.PHONY: ps
ps: ## Show dev services status
	$(DC_DEV) ps

# ══════════════════════════════════════════════════════════════════════════════
#  MIGRATIONS
# ══════════════════════════════════════════════════════════════════════════════

.PHONY: migrate
migrate: _venv-check ## Apply pending migrations (dev)
	$(ALEMBIC) upgrade head

.PHONY: migrate-down
migrate-down: _venv-check ## Rollback the last migration (dev)
	$(ALEMBIC) downgrade -1

.PHONY: revision
revision: _venv-check ## Create a new migration — usage: make revision msg="add users table"
ifndef msg
	$(error Usage: make revision msg="your description")
endif
	$(ALEMBIC) revision --autogenerate -m "$(msg)"

.PHONY: migrate-prod-down
migrate-prod-down: ## Rollback the last migration in production
	$(DC_PROD) run --rm --entrypoint="" app alembic downgrade -1

# ══════════════════════════════════════════════════════════════════════════════
#  PROD
#
#  Mode A — code on the VPS:   make prod / make prod-update
#  Mode B — CI/CD + registry:  make prod-pull   (set DOCKER_IMAGE in .env)
# ══════════════════════════════════════════════════════════════════════════════

.PHONY: push
push: ## Build and push image to the registry (set DOCKER_IMAGE in .env)
	$(DC_PROD) build app
	docker push $$(grep '^DOCKER_IMAGE=' .env | cut -d= -f2)

.PHONY: prod
prod: ## [Mode A] Build image locally and start the full prod stack
	$(DC_PROD) up -d --build

.PHONY: prod-update
prod-update: ## [Mode A] Rebuild app from updated code and restart
	$(DC_PROD) up -d --build app

.PHONY: prod-pull
prod-pull: ## [Mode B] Pull latest image from registry and restart
	$(DC_PROD) pull app
	$(DC_PROD) up -d app

.PHONY: prod-down
prod-down: ## Stop the production stack
	$(DC_PROD) down

.PHONY: prod-logs
prod-logs: ## Follow production logs (Ctrl+C to stop)
	$(DC_PROD) logs -f

.PHONY: prod-ps
prod-ps: ## Show production services status
	$(DC_PROD) ps

.PHONY: prod-shell
prod-shell: ## Open a shell inside the running app container
	$(DC_PROD) exec app /bin/bash

# ══════════════════════════════════════════════════════════════════════════════
#  TESTS
# ══════════════════════════════════════════════════════════════════════════════

.PHONY: test
test: _venv-check ## Run all tests
	$(PYTEST)

.PHONY: test-cov
test-cov: _venv-check ## Run tests with coverage report
	$(PYTEST) --cov=app --cov-report=term-missing

# ══════════════════════════════════════════════════════════════════════════════
#  CLEAN
# ══════════════════════════════════════════════════════════════════════════════

.PHONY: compile
compile: _venv-check ## Recompile requirements*.txt from *.in source files
	$(PIP_COMPILE) requirements.in     -o requirements.txt
	$(PIP_COMPILE) requirements-dev.in -o requirements-dev.txt

.PHONY: clean
clean: ## Remove Python cache and test artifacts
	find . -type d -name "__pycache__"   -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache"   -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info"    -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc"         -delete 2>/dev/null || true
	find . -type f -name ".coverage"     -delete 2>/dev/null || true
	@echo "Cache cleaned."

.PHONY: nuke
nuke: clean ## Hard reset: venv + dev containers + volumes  ⚠ IRREVERSIBLE
	@echo "WARNING: This will delete venv, Docker volumes, and all dev data."
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	$(DC_DEV) down -v --remove-orphans
	rm -rf .venv venv env
	@echo ""
	@echo "  Done. To start fresh: make setup"
	@echo ""
