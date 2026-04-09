# Makefile for Asset Management System Docker operations

.PHONY: help build up down restart logs clean rebuild

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

build:
	docker-compose --env-file .env.docker build

up:
	docker-compose --env-file .env.docker up -d
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
	docker-compose --env-file .env.docker build --no-cache
	docker-compose --env-file .env.docker up -d
	@echo "✅ Rebuilt and restarted all services"

status:
	docker-compose ps

backend:
	docker-compose logs -f backend

frontend:
	docker-compose logs -f frontend

db:
	docker exec -it asset_management_db psql -U postgres -d asset_management
