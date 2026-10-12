---
name: afterparty
description: Set up, run, query and change Afterparty, the self-hosted Partiful scraper and guest list exporter. Use when the user wants to export Partiful guest lists; find the people they met at Partiful events (founders, investors, engineers and other designations); search or filter those people; export them to CSV for Clay, Apollo, HubSpot or a spreadsheet; set follow-up status and notes; sync Partiful again; install, self-host or deploy Afterparty (Docker, Cloud Run); or change the Afterparty code (designation rules, CSV columns, API routes, migrations).
---

# Afterparty

Afterparty is a self-hosted Partiful scraper and guest list exporter.
It reads the events and the guest lists of a Partiful account through Partiful's web API.
It keeps the data in PostgreSQL and serves a web app and a JSON API.

Source: https://github.com/doluz/afterparty

## Choose the task

| The user wants to | Do this |
|-------------------|---------|
| Install or start Afterparty | Follow "Set up an instance". |
| Read, filter or export people, or set follow-ups | Follow "Use the API". |
| Change the code | Read `references/development.md`. |
| Deploy on a server or Cloud Run | Read `docs/self-hosting.md` in the repository. |

## Set up an instance

You must have Docker with Docker Compose.

1. Get the code:

   ```bash
   git clone https://github.com/doluz/afterparty.git && cd afterparty
   cp .env.example .env
   ```

2. Make an encryption key and write it in `.env` as `ENCRYPTION_KEY`:

   ```bash
   python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
   ```

3. Start the server and PostgreSQL:

   ```bash
   docker compose up -d --build
   ```

4. Make sure that the server is up: `curl -s http://localhost:8080/api/health` must return `{"ok":true}`.
5. Tell the user to open http://localhost:8080 and sign in with an email. Local mode has no password.

### The user must connect Partiful

You cannot do this step for the user. Give the user these instructions:

1. In Afterparty, follow the setup pages. Download the connector and load it in Chrome with **Load unpacked**.
2. Sign in to partiful.com in the same Chrome profile.
3. Select **Connect Partiful**. The first sync starts.

To try Afterparty without a Partiful account, the user selects **Use demo data** on the **Connect Partiful** step.
This button shows only in local mode.

## Use the API

Use the script `scripts/afterparty.py`. It needs Python 3.9 or later and no packages.
Set these environment variables first:

| Variable | Value |
|----------|-------|
| `AFTERPARTY_URL` | The address of the instance. Default: `http://localhost:8080`. |
| `AFTERPARTY_AUTH` | The token from **Settings > API access for agents** in the web app. |
| `AFTERPARTY_EMAIL` | Local mode only: the email that the user signs in with. Use it in place of `AFTERPARTY_AUTH`. |

If you do not have a token, ask the user for it. With Google or email sign-in, the token expires after one hour.

### Commands

```bash
python3 scripts/afterparty.py stats                        # counts and designations
python3 scripts/afterparty.py events                       # all events, with guest counts
python3 scripts/afterparty.py event <event_id>             # one event and its guest list
python3 scripts/afterparty.py people [filters] [--all]     # people, 60 for each page by default
python3 scripts/afterparty.py person <person_id>           # one person and the shared events
python3 scripts/afterparty.py export out.csv [filters] [--ids a,b,c]
python3 scripts/afterparty.py follow-up <person_id> todo|contacted|skip|none [--note TEXT]
python3 scripts/afterparty.py sync [--full] [--wait]       # sync Partiful again
python3 scripts/afterparty.py sync-status
```

### Filters

| Flag | Values |
|------|--------|
| `--q TEXT` | Text in the name or the bio. The search is not case-sensitive and finds parts of words. |
| `--cluster` | `founder`, `investor`, `engineering`, `product`, `design`, `gtm_growth`, `other`, `unknown` (no bio). |
| `--social` | `any`, `linkedin`, `twitter` (X), `instagram`. |
| `--follow-up` | `none`, `todo`, `contacted`, `skip`. |
| `--repeat` | Only people that the user met at more than one event. |
| `--event-id ID` | Only the guest list of this event. Get the IDs from `events`. |

The API has no date filter. To filter by date, read `first_met`, `last_met` or the `events` list of each person.
For each person, `times_met` is the number of shared events.

### Map requests to commands

| Request | Command |
|---------|---------|
| "Founders I met more than once" | `people --cluster founder --repeat --all` |
| "Investors with a LinkedIn link, as a CSV" | `export investors.csv --cluster investor --social linkedin` |
| "Who at the Oktoberfest party works in AI?" | `events` to get the ID, then `people --event-id ID --q AI --all` |
| "Mark Ada as contacted" | `people --q Ada` to get the `person_id`, then `follow-up <person_id> contacted` |
| "Get my latest Partiful events" | `sync --wait`, then `stats` |

For the response fields and the CSV columns, read `references/api.md`.

## Rules

- Do not ask for the Partiful password of the user. Afterparty never uses it.
- Keep `AFTERPARTY_AUTH` secret. Do not write it in files, commits, logs or chat output.
- Use only the data that the API gives. Do not add people, companies or links.
- These people did not agree to receive sales email. Do not send messages for the user. Write a draft only when the user asks for it.
- Afterparty only reads from Partiful. Do not try to post, RSVP or send a message on Partiful.
- Do not make a local-mode instance (`APP_ENV=dev`) available on a network. It has no password.

## Problems

| Symptom | Cause | Action |
|---------|-------|--------|
| HTTP 401 | The token expired or is missing. | Ask the user for a new token from **Settings > API access for agents**. |
| HTTP 403 "This Afterparty is private" | The email is not in `ALLOWED_EMAILS`. | Ask the owner of the instance to add the email. |
| HTTP 409 on `sync` | Partiful is not connected. | Tell the user to connect Partiful. Refer to "The user must connect Partiful". |
| `me` shows `token_error` | Partiful refused the stored session. | Tell the user to select **Reconnect** in **Settings**. |
| `people` returns 0 | The first sync did not finish, or the filters are too narrow. | Run `sync-status`. Then remove filters one at a time. |
