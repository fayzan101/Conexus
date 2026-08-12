.PHONY: help up down logs api web install migrate test helm-template

help:
	@echo "Enterprise Brain MVP"
	@echo "  make up             Start infra (postgres, neo4j, qdrant, redis, minio)"
	@echo "  make down           Stop infra"
	@echo "  make install        Install backend + frontend deps"
	@echo "  make migrate        Run DB migrations"
	@echo "  make api            Run FastAPI (reload)"
	@echo "  make web            Run Next.js dev server"
	@echo "  make test           Run backend tests"
	@echo "  make helm-template  Render Helm chart for staging"

up:
	docker compose up -d postgres neo4j qdrant redis minio minio-init

down:
	docker compose down

logs:
	docker compose logs -f

install:
	cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt || .venv/bin/pip install -r requirements.txt
	cd frontend && npm install

migrate:
	cd backend && ( .venv/Scripts/alembic upgrade head || .venv/bin/alembic upgrade head )

api:
	cd backend && ( .venv/Scripts/uvicorn app.main:app --reload --port 8000 || .venv/bin/uvicorn app.main:app --reload --port 8000 )

web:
	cd frontend && npm run dev

test:
	cd backend && ( .venv/Scripts/pytest -q || .venv/bin/pytest -q )

helm-template:
	helm template eb deploy/helm/enterprise-brain -f deploy/helm/enterprise-brain/values.yaml -f deploy/helm/enterprise-brain/values-staging.yaml
