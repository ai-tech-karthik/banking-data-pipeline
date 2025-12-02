.PHONY: help build up down restart logs clean test validate

# Default target
help:
	@echo "LendingClub Pipeline - Docker Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make validate    - Validate Docker setup"
	@echo "  make build       - Build Docker images"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - View logs from all services"
	@echo "  make logs-web    - View webserver logs"
	@echo "  make logs-daemon - View daemon logs"
	@echo "  make logs-code   - View user code logs"
	@echo "  make ps          - Show service status"
	@echo "  make test        - Run tests inside container"
	@echo "  make shell       - Open shell in user code container"
	@echo "  make clean       - Stop and remove all containers and volumes"
	@echo ""

# Validate setup
validate:
	@bash scripts/validate-setup.sh

# Build Docker images
build:
	docker-compose build

# Start services
up:
	docker-compose up -d
	@echo ""
	@echo "✅ Services started!"
	@echo "   Dagster UI: http://localhost:3000"
	@echo ""
	@echo "View logs with: make logs"

# Stop services
down:
	docker-compose down

# Restart services
restart:
	docker-compose restart

# View logs
logs:
	docker-compose logs -f

logs-web:
	docker-compose logs -f dagster-webserver

logs-daemon:
	docker-compose logs -f dagster-daemon

logs-code:
	docker-compose logs -f dagster-user-code

# Show service status
ps:
	docker-compose ps

# Run tests
test:
	docker-compose exec dagster-user-code pytest

test-unit:
	docker-compose exec dagster-user-code pytest tests/unit/

test-integration:
	docker-compose exec dagster-user-code pytest tests/integration/

test-e2e:
	docker-compose exec dagster-user-code pytest tests/e2e/

# Open shell
shell:
	docker-compose exec dagster-user-code bash

# Clean everything
clean:
	docker-compose down -v
	@echo "✅ All containers and volumes removed"

# Rebuild and restart
rebuild: clean build up
