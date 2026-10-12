# AGENTS.md

Instructions for AI coding agents (Claude Code, Codex, Cursor, Gemini CLI, Copilot and others) in this repository.

## Project

Afterparty is a self-hosted Partiful scraper and guest list exporter.
A FastAPI server reads the events and the guest lists of a Partiful account through Partiful's web API.
It keeps the data in PostgreSQL and serves a React web app and a JSON API.
A Chrome extension, the Afterparty Connector, gives the Partiful session to the server one time.

## Commands

```bash
make setup    # uv sync and npm ci
make dev      # PostgreSQL in Docker (port 54331), web build, server on http://localhost:8080 in local mode
make seed     # demo account demo@example.com with made-up people
make test     # pytest on a real PostgreSQL, with a fake Partiful (needs `make db` or `make dev`)
make lint     # ruff (Python) and oxlint (web)
make smoke    # headless Chromium on every page, while `make dev` runs
```

Do `make test` and `make lint` before you finish a change. Do `make smoke` after a change in `web/`.

## Code map

- `src/afterparty/`: FastAPI server, sync, people queries, CSV export, SQL migrations.
- `src/afterparty/core/`: Partiful data model, payload parser, designation rules.
- `web/`: React 19, Vite, Tailwind CSS v4, TanStack Query. The build goes into `src/afterparty/static/`.
- `extension/`: Afterparty Connector, Chrome Manifest V3.
- `tests/`: pytest. `tests/web_app/conftest.py` has the fake Partiful.
- `docs/`: self-hosting, connector and architecture guides.
- `skills/afterparty/`: an Agent Skill to set up, query and change Afterparty. It includes `scripts/afterparty.py`, a client for the JSON API.

## Rules

- Use made-up data only. Do not commit real guest lists, names, emails, Partiful tokens or `.env`.
- Put the user ID in the filter of each SQL query that reads user data. Each user must see only their own data.
- Each field from Partiful is optional. A missing field must give `None`, not an error.
- Add a database change as a new migration file. Do not edit a released migration.
- If you change the designation rules in `src/afterparty/core/roles.py`, change `web/src/pages/HowItWorks.tsx` too.
- If you change the permissions of the connector, increase `version` in `extension/manifest.json`.
- Do not add code that writes to Partiful. Afterparty only reads.
- Local mode (`APP_ENV=dev`) has no password. Do not make it available on a network.

## More

- Procedures for frequent changes: `skills/afterparty/references/development.md`.
- API routes, filters, response fields and CSV columns: `skills/afterparty/references/api.md`.
- Settings and deployment: `docs/self-hosting.md`.
