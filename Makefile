.PHONY: help install dev run test lint format clean docker-up docker-down migrate railway-deploy

help:
	@echo "AI Chat Backend - Makefile commands"
	@echo ""
	@echo "Development:"
	@echo "  make install        - Install dependencies"
	@echo "  make dev            - Run development server"
	@echo "  make test           - Run tests"
	@echo "  make lint           - Run linters"
	@echo "  make format         - Format code"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up      - Start Docker services"
	@echo "  make docker-down    - Stop Docker services"
	@echo "  make docker-logs    - View Docker logs"
	@echo ""
	@echo "Database:"
	@echo "  make migrate        - Run database migrations"
	@echo "  make migrate-create - Create new migration"
	@echo ""
	@echo "Railway:"
	@echo "  make railway-deploy - Deploy to Railway"
	@echo "  make railway-logs   - View Railway logs"
	@echo ""
	@echo "Utils:"
	@echo "  make clean          - Clean cache and temp files"

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

test:
	pytest -v

test-cov:
	pytest --cov=app --cov-report=html

lint:
	flake8 app/
	mypy app/

format:
	black app/
	isort app/

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f backend

docker-rebuild:
	docker-compose build --no-cache
	docker-compose up -d

migrate:
	alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-down:
	alembic downgrade -1

railway-deploy:
	railway up

railway-logs:
	railway logs

railway-shell:
	railway shell

# Generate secret keys
generate-keys:
	@echo "SECRET_KEY="
	@python -c "import secrets; print(secrets.token_urlsafe(32))"
	@echo ""
	@echo "JWT_SECRET_KEY="
	@python -c "import secrets; print(secrets.token_hex(32))"
