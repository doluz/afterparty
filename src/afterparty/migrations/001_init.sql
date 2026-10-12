-- Afterparty schema v1. Every table except users is scoped by user_id, and
-- every API query filters on it.

CREATE TABLE users (
    id            BIGSERIAL PRIMARY KEY,
    firebase_uid  TEXT NOT NULL UNIQUE,
    email         TEXT NOT NULL,
    name          TEXT,
    photo_url     TEXT,
    status        TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'denied')),
    role          TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    onboarded_at  TIMESTAMPTZ,
    approved_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX users_status_idx ON users (status, created_at DESC);

CREATE TABLE partiful_accounts (
    user_id            BIGINT PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    partiful_uid       TEXT NOT NULL,
    display_name       TEXT,
    refresh_token_enc  BYTEA NOT NULL,
    api_key            TEXT NOT NULL,
    connected_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_sync_at       TIMESTAMPTZ,
    token_error        TEXT
);

CREATE TABLE events (
    user_id            BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    event_id           TEXT NOT NULL,
    title              TEXT NOT NULL DEFAULT '',
    starts_at          TIMESTAMPTZ,
    ends_at            TIMESTAMPTZ,
    timezone           TEXT,
    location           TEXT,
    image_url          TEXT,
    role               TEXT NOT NULL,
    my_rsvp            TEXT,
    partiful_count     INTEGER,
    guest_rows         INTEGER NOT NULL DEFAULT 0,
    hidden_rows        INTEGER NOT NULL DEFAULT 0,
    guests_synced_at   TIMESTAMPTZ,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, event_id)
);
CREATE INDEX events_user_start_idx ON events (user_id, starts_at DESC);

CREATE TABLE guests (
    user_id       BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    event_id      TEXT NOT NULL,
    person_id     TEXT NOT NULL,          -- Partiful user id
    name          TEXT NOT NULL,
    username      TEXT,
    avatar_url    TEXT,
    bio           TEXT,
    rsvp          TEXT,
    plus_ones     INTEGER,
    socials       JSONB NOT NULL DEFAULT '{}'::jsonb,   -- platform -> url
    linkedin_url  TEXT,
    cluster       TEXT NOT NULL DEFAULT 'unknown',
    PRIMARY KEY (user_id, event_id, person_id),
    FOREIGN KEY (user_id, event_id) REFERENCES events (user_id, event_id) ON DELETE CASCADE
);
CREATE INDEX guests_person_idx ON guests (user_id, person_id);

CREATE TABLE follow_ups (
    user_id     BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    person_id   TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'contacted', 'skip')),
    note        TEXT NOT NULL DEFAULT '',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, person_id)
);

CREATE TABLE sync_runs (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    trigger      TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'ok', 'error')),
    phase        TEXT,
    events_total INTEGER NOT NULL DEFAULT 0,
    events_done  INTEGER NOT NULL DEFAULT 0,
    guests       INTEGER NOT NULL DEFAULT 0,
    error        TEXT,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at  TIMESTAMPTZ
);
CREATE INDEX sync_runs_user_idx ON sync_runs (user_id, started_at DESC);
