# Changelog

## 1.0.0 - 2026-10-11

First open-source release.

- Partiful sync through Partiful's web API: home-page events, guest lists (`getGuests`, paginated), host guest lists
  (Firestore and `getUsers`). Daily resync, one running sync per user.
- People list with bios, socials, times met, follow-up status and notes. Text search and filters.
- Designations from bios with keyword rules (`src/afterparty/core/roles.py`), documented on `/how-it-works`.
- People map grouped by designation (d3-hierarchy).
- CSV export of any filter, a selection, or one event's guest list, with a formula-injection guard.
- Local mode (email only) and Firebase sign-in, with an optional `ALLOWED_EMAILS` allowlist.
- Partiful refresh tokens encrypted with `ENCRYPTION_KEY` (Fernet) or Google Cloud KMS.
- Afterparty Connector (Chrome, Manifest V3). Each instance serves a connector zip for its own origin.
- Docker image, `docker-compose.yml`, CI, and self-hosting, connector and architecture guides.
