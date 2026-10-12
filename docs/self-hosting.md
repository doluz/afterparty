# Self-hosting

This guide tells you how to run Afterparty on your computer or on a server.
Afterparty has three parts:

- The Afterparty server: a Python API that also serves the web app.
- A PostgreSQL 16 database.
- The Afterparty Connector: a Chrome extension that each user adds one time.

## Choose a sign-in mode

Afterparty has two sign-in modes.

| Mode | Setting | Use it for |
|------|---------|------------|
| Local mode | `APP_ENV=dev` | A personal instance on your computer. You sign in with an email and no password. |
| Firebase mode | `APP_ENV=prod` | A shared instance on a server. Users sign in with Google or with an email link. |

WARNING: Do not make a local-mode instance available on a network. In local mode, each person who can open the instance can sign in as a different user.

## Run with Docker

You must have Docker with Docker Compose.

1. Copy the settings file:

   ```bash
   cp .env.example .env
   ```

2. Make an encryption key:

   ```bash
   python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
   ```

3. Put the key in `.env` as `ENCRYPTION_KEY`. Keep a copy of the key in a safe location.
4. Start the instance:

   ```bash
   docker compose up -d --build
   ```

5. Open http://localhost:8080 and sign in with your email.

`docker-compose.yml` publishes the port on 127.0.0.1 only. The database data stays in the Docker volume `pgdata`.

CAUTION: Keep a copy of `ENCRYPTION_KEY`. If the key is missing, Afterparty cannot read the stored Partiful sign-ins. Each user must then connect Partiful again.

## Run from source

You must have [uv](https://docs.astral.sh/uv/), Node.js 22 and Docker.

1. Install the dependencies:

   ```bash
   make setup
   ```

2. Start the database, build the web app and start the server:

   ```bash
   make dev
   ```

3. Open http://localhost:8080.

`make dev` starts PostgreSQL in Docker on port 54331. The server makes a local encryption key in `.devdb/fernet.key`.

To see the app with made-up people, run `make seed`. Then sign in as `demo@example.com`.

## Add the connector

Each user adds the Afterparty Connector to Chrome one time. The setup pages in Afterparty show the steps.
For the full procedure, refer to [connector.md](connector.md).

## Set up Firebase sign-in

Use Firebase mode for an instance that other people can open.

1. Make a project in the [Firebase console](https://console.firebase.google.com).
2. Open **Authentication** and enable the **Google** provider.
3. Optional: enable **Email/Password** with **Email link (passwordless sign-in)**.
4. In **Authentication > Settings > Authorized domains**, add the domain of your instance.
5. Open **Project settings > General**. Add a web app and copy its configuration.
6. Set these values in `.env`:

   ```bash
   APP_ENV=prod
   FIREBASE_PROJECT_ID=your-project-id
   FIREBASE_WEB_CONFIG={"apiKey":"...","authDomain":"your-project-id.firebaseapp.com","projectId":"your-project-id","appId":"..."}
   ALLOWED_EMAILS=you@example.com,@yourcompany.com
   PUBLIC_URL=https://afterparty.example.com
   ```

`ALLOWED_EMAILS` sets who can sign in. Write full addresses, or `@domain` for all addresses of a domain.
If `ALLOWED_EMAILS` is empty, each person who can sign in with Firebase can use the instance.
Each user sees only the data of that user.
The Firebase web configuration is public data, not a secret.

## Put the instance on a server

1. Use a server that can run Docker, or a platform that can run a container image.
2. Put a reverse proxy with HTTPS in front of the container. Caddy, nginx and Traefik are examples.
3. Set `PUBLIC_URL` to the HTTPS address of the instance.
4. Use Firebase mode.

The connector accepts messages only from the address in `PUBLIC_URL`.
If you change `PUBLIC_URL`, each user must download the connector again.

## Sync every day

Afterparty reads the guest lists again one time each day. Use one of these methods:

- Set `BACKGROUND_SYNC=true`. The server does the sync. Use this method on one server.
- Set `CRON_SECRET` to a long random value. Then send this request one time each day from a scheduler:

  ```bash
  curl -X POST -H "Authorization: Bearer $CRON_SECRET" https://afterparty.example.com/internal/sync-all
  ```

A sync skips the users that Afterparty synced in the last 20 hours.

## Deploy on Google Cloud Run

You can run the same image on Cloud Run with Cloud SQL for PostgreSQL.

1. Build the image with Cloud KMS support:

   ```bash
   gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT/afterparty/app --build-arg EXTRAS=gcp
   ```

2. Make a Cloud SQL instance with PostgreSQL 16. Keep the connection string in Secret Manager.
3. Optional: make a Cloud KMS key. Give the Cloud Run service account the role `roles/cloudkms.cryptoKeyEncrypterDecrypter`. Set `KMS_KEY` to the full key name.
4. Deploy the service with the values from `.env.example`. Set `PUBLIC_URL` to the service URL or to your domain.
5. Make a Cloud Scheduler job that sends `POST /internal/sync-all` one time each day. Use `CRON_SECRET`, or an OIDC token for the account in `SCHEDULER_SA`.

When `KMS_KEY` is set, only the service account can decrypt the Partiful sign-ins. A copy of the database without the key does not show them.

## Update to a new version

1. Get the new code:

   ```bash
   git pull
   ```

2. Build and start the instance again:

   ```bash
   docker compose up -d --build
   ```

The server applies new database migrations when it starts.

## Make a backup

The database has all the data. The encryption key is necessary to read the stored Partiful sign-ins.

```bash
docker compose exec db pg_dump -U afterparty afterparty > afterparty-backup.sql
```

Keep the backup and `ENCRYPTION_KEY` in different locations.

## Settings

| Variable | Default | Function |
|----------|---------|----------|
| `ENCRYPTION_KEY` | none (required) | Encrypts the Partiful sign-ins in the database. |
| `DATABASE_URL` | none (required) | PostgreSQL connection string. |
| `APP_ENV` | `prod` | `dev` is local mode. `prod` is Firebase mode. |
| `FIREBASE_PROJECT_ID` | none | Firebase project that issues the sign-in tokens. |
| `FIREBASE_WEB_CONFIG` | `{}` | Public Firebase web configuration, as JSON on one line. |
| `ALLOWED_EMAILS` | none | Addresses and `@domain` entries that can sign in. Separate them with commas. Empty lets all users sign in. |
| `PUBLIC_URL` | `http://localhost:8080` | Address of the instance. The connector accepts messages only from this address. |
| `BACKGROUND_SYNC` | `false` | Sync all users one time each day from the server process. |
| `CRON_SECRET` | none | Bearer token for `POST /internal/sync-all`. |
| `EXTENSION_ID` | ID of the unpacked connector | Connector IDs, separated by commas. Add your Chrome Web Store item ID here. |
| `CONNECTOR_STORE_URL` | none | Chrome Web Store page of your connector. The setup page then shows "Add to Chrome". |
| `PARTIFUL_DELAY` | `0.3` | Seconds between two Partiful requests during a sync. |
| `KMS_KEY` | none | Google Cloud KMS key that encrypts in place of `ENCRYPTION_KEY`. |
| `SERVICE_URL`, `SCHEDULER_SA` | none | Accept the OIDC token from Google Cloud Scheduler. |

## Problems

| Symptom | Cause | Action |
|---------|-------|--------|
| The server stops at start with "Set ENCRYPTION_KEY". | `.env` has no key. | Make a key. Refer to "Run with Docker". |
| The setup page shows "Waiting for the connector". | The connector is not in Chrome, or it does not accept this address. | Download the connector from this instance again. Load it again. |
| A user sees "Your Partiful session expired". | Partiful refused the stored sign-in. | The user selects **Reconnect** in Settings. |
| A sync ends with "Could not read N events". | Partiful refused some guest lists. The other events are complete. | No action. The next sync tries again. |
