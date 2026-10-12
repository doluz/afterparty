-- The open-source build has no admin approval: everyone who can sign in (and
-- passes ALLOWED_EMAILS) uses the app. Drop the access-control columns.

DROP INDEX IF EXISTS users_status_idx;
ALTER TABLE users DROP COLUMN IF EXISTS status;
ALTER TABLE users DROP COLUMN IF EXISTS role;
ALTER TABLE users DROP COLUMN IF EXISTS approved_at;
