.PHONY: help up down restart logs ingest psql ollama-logs

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services in the background (detached mode)
	docker compose up --build -d

down: ## Stop and remove all services
	docker compose down

restart: ## Restart all services
	docker compose restart

logs: ## Tail logs for all services
	docker compose logs -f

ingest: ## Run the data ingestion script to populate pgvector
	docker compose run --rm ingest

psql: ## Access the PostgreSQL database via psql
	docker compose exec db psql -U lenny -d lenny_db

ollama-logs: ## View Ollama logs
	docker compose logs -f ollama
