# Afterparty API reference

All routes under `/api/` need the header `Authorization`, except `/api/health` and `/api/config`.
The header value is `Bearer <Firebase ID token>`, or `Dev <email>` in local mode.
Each response contains only the data of the user who sends the request.
The machine-readable schema is at `/openapi.json` on each instance.

## Routes

| Method and path | Body or query | Response |
|-----------------|---------------|----------|
| `GET /api/health` | | `{"ok": true}` |
| `GET /api/me` | | `user`, `partiful` (or `null`), `sync` (last run or `null`) |
| `DELETE /api/me` | | Deletes the account and all its data. |
| `DELETE /api/partiful` | | Deletes the stored Partiful session. The events and notes stay. |
| `POST /api/sync` | `{"full": false}` | A sync run. HTTP 409 if Partiful is not connected. |
| `GET /api/sync` | | The last sync run, or `null`. |
| `GET /api/stats` | | Counts for the home page. |
| `GET /api/events` | | A list of events. |
| `GET /api/events/{event_id}` | | `{"event": {...}, "guests": [...]}` |
| `GET /api/people` | filters, `limit` (1 to 200, default 60), `offset` | `{"total": n, "people": [...]}` |
| `GET /api/people/{person_id}` | | One person and the shared events. |
| `GET /api/people/map` | filters | `{"total": n, "people": [...]}` with fewer fields |
| `POST /api/people/export` | filters as JSON, plus optional `ids` | A CSV file. The header `X-Afterparty-Rows` gives the row count. |
| `PUT /api/people/{person_id}/follow-up` | `{"status": "todo", "note": "..."}` | `{"ok": true}` |

## Filters

Send the filters as query parameters on `GET` routes and as JSON on `POST /api/people/export`.

| Name | Type | Values |
|------|------|--------|
| `q` | text | Text in the name or the bio. Not case-sensitive. Finds parts of words. |
| `cluster` | text | `founder`, `investor`, `engineering`, `product`, `design`, `gtm_growth`, `other`, `unknown` |
| `social` | text | `any`, `linkedin`, `twitter`, `instagram` |
| `follow_up` | text | `none`, `todo`, `contacted`, `skip` |
| `repeat` | boolean | `true` gives only the people met at more than one event. |
| `event_id` | text | Only the guest list of this event. |
| `ids` | list of text | Export only: these `person_id` values. |

## Person

```json
{
  "person_id": "demo-148",
  "name": "Blake Quintero",
  "username": null,
  "avatar_url": null,
  "bio": "Co-founder & CEO at Saltbox. Building robotics.",
  "socials": {"twitter": "https://x.com/blake148"},
  "linkedin_url": null,
  "cluster": "founder",
  "times_met": 3,
  "first_met": "2026-09-13T19:45:24+00:00",
  "last_met": "2026-10-05T02:45:24+00:00",
  "events": [{"id": "demo-ev-2", "title": "Oktoberfest Block Party", "starts_at": "2026-10-05T02:45:24+00:00"}],
  "follow_up": "none",
  "note": ""
}
```

- `person_id` is the Partiful user ID. It is the same in all events.
- `socials` can contain `twitter`, `instagram`, `tiktok`, `facebook` and other links that the person made visible.
- `times_met` counts the events that the user attended, or hosted after they started.

## Event

Fields of each item in `GET /api/events`:
`id`, `title`, `starts_at`, `ends_at`, `timezone`, `location`, `image_url`, `role`, `my_rsvp`, `partiful_count`,
`guest_rows`, `hidden_rows`, `guests_synced_at`, `guests`, `reachable`.

`role` is one of `attended`, `hosting`, `going`, `upcoming`, `waitlisted`, `pending`, `maybe`, `followed`, `saved` or `unknown`.
`hidden_rows` counts the guests that Partiful hides from the user.

## Stats

```json
{
  "events_attended": 8,
  "events_upcoming": 2,
  "people": 244,
  "reachable": 157,
  "repeat": 133,
  "contacted": 1,
  "clusters": {"founder": 51, "investor": 37, "engineering": 36, "product": 29, "design": 13, "gtm_growth": 18, "other": 24, "unknown": 36}
}
```

`reachable` counts the people with one or more social links.

## Sync run

```json
{
  "id": 2,
  "trigger": "manual",
  "status": "ok",
  "phase": "done",
  "events_total": 10,
  "events_done": 10,
  "guests": 536,
  "error": null,
  "started_at": "2026-10-12T04:45:24+00:00",
  "finished_at": "2026-10-12T04:45:32+00:00"
}
```

`status` is `running`, `ok` or `error`. When `status` is `ok`, `error` can tell you about events that Partiful refused.

## CSV columns

`name`, `first_name`, `last_name`, `designation`, `company_from_bio`, `bio`, `linkedin_url`, `x_url`, `instagram_url`,
`tiktok_url`, `facebook_url`, `partiful_url`, `times_met`, `events`, `first_met`, `last_met`, `follow_up`, `note`,
`partiful_user_id`

- The file is UTF-8 with a byte order mark.
- `company_from_bio` is the name after "at" or "@" in the bio. It is empty if the bio does not use that form.
- A cell that starts with `=`, `+`, `-`, `@` or a tab gets an apostrophe in front. This prevents formula injection.
