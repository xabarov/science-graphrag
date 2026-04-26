.DEFAULT_GOAL := help

COMPOSE_PROD = docker compose -f docker-compose.prod.yml
COMPOSE_DEV = docker compose -f docker-compose.dev.yml

.PHONY: help quality prod-up prod-down prod-build prod-logs prod-ps prod-restart dev-up dev-down dev-build dev-logs dev-ps dev-restart dev-recreate-api dev-ui-modules-reset

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_.-]+:.*## / {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

quality: ## Backend: isort/black check + pylint (same as CI lint gate)
	.venv/bin/isort --check-only science_graphrag tests
	.venv/bin/black --check science_graphrag tests
	.venv/bin/pylint science_graphrag tests --fail-under=7.0

prod-up: ## Start prod-like stack in background
	$(COMPOSE_PROD) up -d --build

prod-down: ## Stop prod-like stack
	$(COMPOSE_PROD) down

prod-build: ## Rebuild prod-like images
	$(COMPOSE_PROD) build

prod-logs: ## Tail prod-like stack logs
	$(COMPOSE_PROD) logs -f

prod-ps: ## Show prod-like stack status
	$(COMPOSE_PROD) ps

prod-restart: ## Restart prod-like stack with rebuild
	$(COMPOSE_PROD) down
	$(COMPOSE_PROD) up -d --build

dev-up: ## Start dev stack with backend/frontend hot reload
	$(COMPOSE_DEV) up -d --build

dev-down: ## Stop dev stack
	$(COMPOSE_DEV) down

dev-build: ## Rebuild dev stack images
	$(COMPOSE_DEV) build

dev-logs: ## Tail dev stack logs
	$(COMPOSE_DEV) logs -f

dev-ps: ## Show dev stack status
	$(COMPOSE_DEV) ps

dev-restart: ## Restart dev stack with rebuild
	$(COMPOSE_DEV) down
	$(COMPOSE_DEV) up -d --build

dev-recreate-api: ## Recreate api only (pick up compose env, e.g. SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV)
	$(COMPOSE_DEV) up -d api --force-recreate

# Stop ui first so Vite does not touch node_modules while npm ci runs (named volume).
dev-ui-modules-reset: ## Reinstall ui/node_modules in the dev volume (fix missing/corrupt deps in Docker)
	$(COMPOSE_DEV) stop ui
	$(COMPOSE_DEV) run --rm --no-deps ui sh -c 'cd /app/ui && rm -rf node_modules/* node_modules/.[!.]* node_modules/..?* 2>/dev/null; npm ci && (cat package.json && cat package-lock.json) | md5sum | cut -d" " -f1 > node_modules/.deps_hash'
	$(COMPOSE_DEV) start ui
