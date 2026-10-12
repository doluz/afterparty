# Afterparty developer shortcuts. Needs uv, Node 22 and Docker.

.PHONY: setup db web dev seed test lint smoke docker connector

setup:            ## install Python and web dependencies
	uv sync
	npm --prefix web ci --no-audit --no-fund

db:               ## start the local Postgres (Docker, port 54329)
	scripts/devdb.sh start

web:              ## build the web app into src/afterparty/static
	npm --prefix web run build

dev: db web       ## run Afterparty in local mode on http://localhost:8080
	uv run afterparty-dev

seed: db          ## a demo account with made-up people: sign in as demo@example.com
	uv run python scripts/seed_demo.py

test: db          ## API and parser tests
	uv run pytest -q

lint:
	uv run ruff check src tests scripts
	uv run ruff format --check src tests scripts
	npm --prefix web run lint

smoke:            ## every page in a headless browser (needs `make dev` running)
	uv run playwright install chromium
	uv run python scripts/ui_smoke.py

docker:           ## the app and Postgres in Docker on http://localhost:8080
	docker compose up -d --build

connector:        ## the connector zip for PUBLIC_URL (default localhost)
	uv run python scripts/package_extension.py dist/afterparty-extension.zip --url $${PUBLIC_URL:-http://localhost:8080}
