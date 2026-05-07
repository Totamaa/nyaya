# ══════════════════════════════════════════════════════════════════════════════
#  Nyaya — Developer Makefile
#  Compatible: Linux / macOS / Windows (Git Bash)
# ══════════════════════════════════════════════════════════════════════════════

APP_ENTRY := src/app/main.py

# ── Virtualenv configuration ──────────────────────────────────────────────────
ifeq ($(OS),Windows_NT)
  VENV_BIN           := .venv/Scripts
  PYTHON_SYSTEM      := py
  TASKIQ_WORKER_OPTS :=
else
  VENV_BIN           := .venv/bin
  PYTHON_SYSTEM      := python3
  TASKIQ_WORKER_OPTS := --reload
endif

PYTHON      := $(VENV_BIN)/python
PIP         := $(VENV_BIN)/pip
UV          := $(VENV_BIN)/uv
FASTAPI     := $(VENV_BIN)/fastapi
ALEMBIC     := $(VENV_BIN)/alembic
PYTEST      := $(VENV_BIN)/pytest
TASKIQ      := $(VENV_BIN)/taskiq

.PHONY: _venv-check
_venv-check:
	@test -f $(PYTHON) \
		|| (echo "" \
		&&  echo "  ERROR: virtual environment not found." \
		&&  echo "  Run:   make setup" \
		&&  echo "" \
		&&  exit 1)

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
#  SETUP
# ══════════════════════════════════════════════════════════════════════════════

.PHONY: venv
venv: ## Create the virtual environment (.venv) and install uv
	$(PYTHON_SYSTEM) -m venv .venv
	$(PIP) install uv

.PHONY: install
install: _venv-check ## Install dependencies for the first time
	$(UV) pip install -r requirements-dev.txt
	$(UV) pip install -e .

.PHONY: setup
setup: venv compile sync ## First-time setup: venv → compile → sync → migrate
	@echo ""
	@echo "  Setup complete. Run 'make dev'."
	@echo ""

# ══════════════════════════════════════════════════════════════════════════════
#  LOCAL DEV
# ══════════════════════════════════════════════════════════════════════════════

.PHONY: up
up: ## Start dev services (Postgres + Redis)
	docker compose up -d
	@echo "Waiting for Postgres..."
	@until docker compose exec -T postgres pg_isready -q 2>/dev/null; do printf "."; sleep 1; done
	@echo " ready."

.PHONY: sync
sync: _venv-check up ## Recompile deps + sync venv + apply migrations
	$(UV) pip compile --universal --upgrade requirements.in     -o requirements.txt
	$(UV) pip compile --universal --upgrade requirements-dev.in -o requirements-dev.txt
	$(UV) pip sync requirements.txt requirements-dev.txt
	$(UV) pip install --no-deps -e .
	$(ALEMBIC) upgrade head

.PHONY: dev
dev: _venv-check up migrate ## Start API + worker (Ctrl+C stops all)
	@trap 'kill 0' INT TERM; \
	$(TASKIQ) worker app.core.config.broker:broker app.background.tasks $(TASKIQ_WORKER_OPTS) & \
	$(FASTAPI) dev $(APP_ENTRY) & \
	wait

.PHONY: down
down: ## Stop dev services
	docker compose down

.PHONY: logs
logs: ## Follow dev services logs (Ctrl+C to stop)
	docker compose logs -f

.PHONY: ps
ps: ## Show dev services status
	docker compose ps

.PHONY: trigger-review
trigger-review: _venv-check ## Manually enqueue the monthly review (for testing)
	$(PYTHON) scripts/trigger_monthly_review.py

# ══════════════════════════════════════════════════════════════════════════════
#  DATABASE MIGRATIONS
# ══════════════════════════════════════════════════════════════════════════════

.PHONY: migrate
migrate: _venv-check ## Apply pending migrations
	$(ALEMBIC) upgrade head

.PHONY: migrate-down
migrate-down: _venv-check ## Rollback the last migration
	$(ALEMBIC) downgrade -1

.PHONY: revision
revision: _venv-check ## Create a new migration — usage: make revision msg="add users table"
ifndef msg
	$(error Usage: make revision msg="your description")
endif
	$(ALEMBIC) revision --autogenerate -m "$(msg)"

.PHONY: db-reset
db-reset: _venv-check ## Wipe Postgres container + volume, recreate and migrate  ⚠ DEV ONLY
	@echo "WARNING: Postgres container and data volume will be destroyed."
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	docker compose rm -sf postgres
	docker volume rm nyaya-backend_postgres_data 2>/dev/null || true
	docker compose up -d postgres
	@echo "Waiting for Postgres..."
	@until docker compose exec -T postgres pg_isready -q 2>/dev/null; do printf "."; sleep 1; done
	@echo " ready."
	$(ALEMBIC) upgrade head

# ══════════════════════════════════════════════════════════════════════════════
#  TESTS
# ══════════════════════════════════════════════════════════════════════════════

.PHONY: test
test: _venv-check up ## Run all tests
	$(PYTEST)

.PHONY: test-cov
test-cov: _venv-check ## Run tests with coverage report
	$(PYTEST) --cov=app --cov-report=term-missing

# ══════════════════════════════════════════════════════════════════════════════
#  CLEAN
# ══════════════════════════════════════════════════════════════════════════════

.PHONY: compile
compile: _venv-check ## Recompile requirements*.txt from *.in source files
	$(UV) pip compile --universal requirements.in     -o requirements.txt
	$(UV) pip compile --universal requirements-dev.in -c requirements.txt -o requirements-dev.txt

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
	docker compose down -v --remove-orphans
	rm -rf .venv venv env
	@echo ""
	@echo "  Done. To start fresh: make setup"
	@echo ""
