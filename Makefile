# Makefile for Asset Management System Docker operations

.PHONY: help build up down restart logs clean rebuild setup

help:
	@echo "Asset Management System - Docker Commands"
	@echo ""
	@echo "Usage: make [command]"
	@echo ""
	@echo "Commands:"
	@echo "  build      - Build all Docker images"
	@echo "  up         - Start all services"
	@echo "  down       - Stop all services"
	@echo "  restart    - Restart all services"
	@echo "  logs       - View logs from all services"
	@echo "  clean      - Remove all containers, volumes, and images"
	@echo "  rebuild    - Rebuild and restart all services"
	@echo "  status     - Show status of all services"
	@echo "  backend    - View backend logs"
	@echo "  frontend   - View frontend logs"
	@echo "  db         - Connect to PostgreSQL database"
	@echo "  dast       - Run OWASP ZAP full active scan (needs 'make up' running)"
	@echo "  setup      - Install pre-commit hooks (run once after cloning)"

setup:
	@echo "Installing pre-commit..."
	pip install pre-commit
	pre-commit install
	@echo "Pre-commit hooks installed. Secret scan + lint will run on every git commit."

build:
	docker-compose --env-file .env build

up:
	docker-compose --env-file .env up -d
	@echo ""
	@echo "✅ All services started!"
	@echo ""
	@echo "Access points:"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  Backend:   http://localhost:8000"
	@echo "  API Docs:  http://localhost:8000/docs"
	@echo "  pgAdmin:   http://localhost:5050"
	@echo ""

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

clean:
	docker-compose down -v --rmi all
	@echo "✅ Cleaned up all containers, volumes, and images"

rebuild:
	docker-compose down
	docker-compose --env-file .env build --no-cache
	docker-compose --env-file .env up -d
	@echo "✅ Rebuilt and restarted all services"

status:
	docker-compose ps

backend:
	docker-compose logs -f backend

frontend:
	docker-compose logs -f frontend

db:
	docker exec -it asset_management_db psql -U postgres -d asset_management

# Run the OWASP ZAP full active scan locally (headless), same automation
# plan the CI dast-scan job uses. Requires `make up` running first.
dast:
	@echo "Running OWASP ZAP full active scan against the local stack..."
	docker run --rm \
		--network eamsagemcom_asset_management_network \
		--env-file .env \
		-v "$(CURDIR)/security/zap:/zap/wrk:rw" \
		ghcr.io/zaproxy/zaproxy:stable \
		zap.sh -cmd -autorun /zap/wrk/zap-automation.yaml
	@echo ""
	@echo "Done. Report: security/zap/zap-report.html"

# ── Security monitoring stack ─────────────────────────────────────────────────

monitoring-up:
	docker compose -f docker-compose.monitoring.yml up -d --build
	@echo ""
	@echo "Security monitoring started!"
	@echo "  Grafana:     http://localhost:3001  (admin / see GRAFANA_PASSWORD)"
	@echo "  Prometheus:  http://localhost:9095  (9090 = SonarQube)"
	@echo "  Pushgateway: http://localhost:9091"
	@echo ""

monitoring-down:
	docker compose -f docker-compose.monitoring.yml down

monitoring-logs:
	docker compose -f docker-compose.monitoring.yml logs -f

monitoring-status:
	docker compose -f docker-compose.monitoring.yml ps

monitoring-clean:
	docker compose -f docker-compose.monitoring.yml down -v
	@echo "Monitoring stack stopped and volumes removed"

# Manual Trivy scan + push (runs outside CI — useful for local dev)
scan-and-push:
	@echo "Running local Trivy scan and pushing metrics..."
	@for img in eam-backend eam-frontend eam-ml-microservice eam-rag-service; do \
		echo "Scanning $$img:latest ..."; \
		docker run --rm \
			-v /var/run/docker.sock:/var/run/docker.sock:ro \
			-v /tmp:/out \
			aquasec/trivy:latest image \
			--format json --output /out/trivy-$$img.json \
			--severity CRITICAL,HIGH,MEDIUM,LOW \
			$$img:latest 2>/dev/null || true; \
		[ -f /tmp/trivy-$$img.json ] && \
			python3 monitoring/scripts/trivy_push_metrics.py \
				/tmp/trivy-$$img.json $$img:latest http://localhost:9091 || true; \
	done
	@echo "Done. Check Grafana at http://localhost:3001"
