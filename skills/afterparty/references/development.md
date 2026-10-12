# Change the Afterparty code

Read this file before you change the Afterparty code. The repository is https://github.com/doluz/afterparty.
The file `AGENTS.md` at the root of the repository has the same commands and rules.

## Set up

You must have uv, Node.js 22 and Docker.

```bash
make setup    # Python and web dependencies
make dev      # PostgreSQL in Docker (port 54331), web build, server on http://localhost:8080
make seed     # demo account demo@example.com with made-up people
```

## Do the checks

Do these checks before you finish a change:

```bash
make test     # pytest on a real PostgreSQL, with a fake Partiful
make lint     # ruff and oxlint
make smoke    # headless Chromium on every page, while `make dev` runs
```

`make test` needs the database from `make dev` or `make db`.

## Code map

| Path | Contents |
|------|----------|
| `src/afterparty/app.py` | FastAPI routes, security headers, the SPA fallback |
| `src/afterparty/auth.py` | Firebase token check, local mode, `ALLOWED_EMAILS`, scheduler auth |
| `src/afterparty/sync.py` | Sync of one user: events, guest lists, progress, daily sync |
| `src/afterparty/partiful_api.py` | Partiful client: token refresh, retries, guest lists, Firestore |
| `src/afterparty/core/parse.py` | Partiful payload rows to `Event` and `Guest` |
| `src/afterparty/core/roles.py` | Designation rules for bios |
| `src/afterparty/people.py` | People queries, filters, CSV export |
| `src/afterparty/connector.py` | Connector zip for the origin of the instance |
| `src/afterparty/migrations/` | SQL migrations, applied in name order at start |
| `web/src/pages/` | React pages |
| `web/src/lib/api.ts` | API client and TanStack Query hooks |
| `extension/` | Afterparty Connector (Chrome, Manifest V3) |
| `tests/web_app/` | API tests with a fake Partiful (`conftest.py`) |

## Rules

- Use made-up data only, in code, tests, screenshots and issues. Do not commit real guest lists, names or tokens.
- Put the user ID in the filter of each SQL query that reads user data.
- Each field from Partiful is optional. A missing field must give `None`, not an error.
- Add a database change as a new file `src/afterparty/migrations/NNN_name.sql`. Do not edit a released migration.
- If you change the permissions or `externally_connectable` in `extension/manifest.json`, increase `version`.
- Write a test for each change in behavior.

## Procedures

### Add a designation

1. Add the group and its words to `src/afterparty/core/roles.py`. The order of the groups is the order of the checks.
2. Add the label to `CLUSTERS` in `web/src/lib/format.ts`.
3. Add the group to the rules on `web/src/pages/HowItWorks.tsx`.
4. Add cases to `tests/test_roles.py`.
5. Do the checks. Each sync applies the new rules to the stored bios again.

### Add a CSV column

1. Add the name to `CSV_COLUMNS` in `src/afterparty/people.py`.
2. Add the value in `to_csv` in the same file.
3. Add an assertion to the export test in `tests/web_app/test_api.py`.
4. Add the column to the list in `README.md` and in `skills/afterparty/references/api.md`.

### Add an API route

1. Add the route to `src/afterparty/app.py` with `user: dict = Depends(current_user)`.
2. Put `user["id"]` in the filter of each query.
3. Add a hook in `web/src/lib/api.ts` if the web app uses the route.
4. Add a test in `tests/web_app/`, and a test that a second user cannot read the data.
5. Add the route to `skills/afterparty/references/api.md`.
