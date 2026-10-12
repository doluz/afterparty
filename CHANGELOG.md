# Changelog

## 1.0.0 - 2026-10-11

First open-source release.

- Connect Partiful through the Afterparty Connector, then sync every event and guest list you can see.
- People list with bios, socials, times met, follow-up status and notes.
- Designations from bios (Founder, Investor, Engineer, Product, Design, GTM and growth), explained on `/how-it-works`.
- People Map grouped by designation.
- CSV export of any filter, a selection, or one event's guest list.
- Local mode for a personal instance, Firebase sign-in for a shared one, with admin approval or auto-approve.
- Docker image and `docker-compose.yml`. Daily sync in the server process or through `/internal/sync-all` with a shared secret.
- Each instance serves a connector zip for its own address.
