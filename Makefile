# ──────────────────────────────────────────────────────────────
#  Lyre – Makefile
#  A self-hostable "now listening" bot for Misskey/Mastodon
# ──────────────────────────────────────────────────────────────

PYTHON   ?= python
PIP      ?= pip
VENV_DIR ?= venv

.PHONY: help install update run docker-build docker-up docker-down docker-status clean lint test encrypt-config

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────────

install: ## Create venv and install dependencies
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip
	$(VENV_DIR)/bin/pip install -r requirements.txt
	@echo "\nInstalled. Activate with: source $(VENV_DIR)/bin/activate"

update: ## Pull latest code, reinstall deps, and rebuild Docker image
	git pull
	$(PIP) install -r requirements.txt
	docker build -t lyre:latest .
	@echo "\nUpdate complete."

# ── Run ──────────────────────────────────────────────────────

run: ## Run the bot
	$(PYTHON) -m lyre

run-verbose: ## Run the bot with debug logging
	$(PYTHON) -m lyre --verbose

# ── Docker ───────────────────────────────────────────────────

build: ## Build the Docker image
	docker build -t lyre:latest .

up: ## Start Lyre via docker-compose (background)
	docker-compose up -d

down: ## Stop Lyre via docker-compose
	docker-compose down

status: ## Check if a Lyre container is running
	@docker ps --filter "name=lyre-bot" --format "table {{.ID}}\t{{.Status}}\t{{.Names}}" || echo "Docker not available."

logs: ## Tail logs from the running container
	docker-compose logs -f

# ── Quality ──────────────────────────────────────────────────

lint: ## Run linter (ruff)
	$(PYTHON) -m ruff check lyre/

test: ## Run tests with pytest
	$(PYTHON) -m pytest

# ── Utilities ────────────────────────────────────────────────

encrypt-config: ## Encrypt sensitive fields in the config file
	$(PYTHON) -m lyre --encrypt-config

# ── Cleanup ──────────────────────────────────────────────────

clean: ## Remove build artefacts, caches, and venv
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf $(VENV_DIR) build/ dist/ *.egg-info .pytest_cache .ruff_cache
	@echo "Cleaned."
