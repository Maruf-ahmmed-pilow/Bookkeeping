.DEFAULT_GOAL := help
.PHONY: help db backend-install backend-seed backend-run backend-lint backend-test \
        frontend-install frontend-run frontend-lint frontend-build test lint up down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

## --- Infrastructure ---
db: ## Start Postgres (host port 5433)
	docker compose up -d db

up: ## Build & run the full stack in Docker (db + backend + frontend)
	docker compose --profile full up --build

down: ## Stop all containers
	docker compose --profile full down

## --- Backend ---
backend-install: ## Install backend dev dependencies
	cd backend && pip install -r requirements-dev.txt

backend-seed: ## Seed the database (Chart of Accounts + sample transactions)
	cd backend && python -m app.seed

backend-run: ## Run the FastAPI dev server (http://localhost:8000)
	cd backend && python -m uvicorn app.main:app --reload

backend-lint: ## Lint the backend with ruff
	cd backend && python -m ruff check .

backend-test: ## Run backend tests
	cd backend && python -m pytest

## --- Frontend ---
frontend-install: ## Install frontend dependencies
	cd frontend && npm install

frontend-run: ## Run the Vite dev server (http://localhost:5173)
	cd frontend && npm run dev

frontend-lint: ## Lint & typecheck the frontend
	cd frontend && npm run lint && npm run typecheck

frontend-build: ## Production build of the frontend
	cd frontend && npm run build

## --- Aggregate ---
lint: backend-lint frontend-lint ## Lint everything
test: backend-test ## Run all tests
