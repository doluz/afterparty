-- One running sync per user, liveness by heartbeat, and notes without a status.

-- Close duplicate running runs before the unique index can exist.
UPDATE sync_runs r SET status = 'error', finished_at = now(), error = 'Superseded by a newer sync.'
WHERE status = 'running'
  AND EXISTS (
      SELECT 1 FROM sync_runs n
      WHERE n.user_id = r.user_id AND n.status = 'running' AND n.started_at > r.started_at
  );

ALTER TABLE sync_runs ADD COLUMN heartbeat_at TIMESTAMPTZ;
CREATE UNIQUE INDEX sync_runs_one_running ON sync_runs (user_id) WHERE status = 'running';

-- A note can exist with no follow-up status ("none").
ALTER TABLE follow_ups DROP CONSTRAINT follow_ups_status_check;
ALTER TABLE follow_ups ADD CONSTRAINT follow_ups_status_check
    CHECK (status IN ('none', 'todo', 'contacted', 'skip'));
