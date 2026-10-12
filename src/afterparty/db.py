"""Postgres access: one connection pool, plain SQL, numbered migrations."""

from __future__ import annotations

from contextlib import contextmanager
from importlib import resources

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import settings

_pool: ConnectionPool | None = None


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is not set")
        _pool = ConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=8,
            kwargs={"row_factory": dict_row, "autocommit": True},
            open=True,
        )
    return _pool


def close() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def conn():
    with pool().connection() as c:
        yield c


def one(sql: str, params: tuple | dict = ()) -> dict | None:
    with conn() as c:
        return c.execute(sql, params).fetchone()


def all_(sql: str, params: tuple | dict = ()) -> list[dict]:
    with conn() as c:
        return c.execute(sql, params).fetchall()


def run(sql: str, params: tuple | dict = ()) -> int:
    with conn() as c:
        return c.execute(sql, params).rowcount


def migrate() -> list[str]:
    """Apply every migrations/NNN_*.sql not yet recorded, in order, each in a
    transaction. An advisory lock keeps two starting instances from racing."""
    applied: list[str] = []
    files = sorted(
        (f for f in resources.files("afterparty.migrations").iterdir() if f.name.endswith(".sql")),
        key=lambda f: f.name,
    )
    with conn() as c:
        c.execute("SELECT pg_advisory_lock(7420151)")
        try:
            c.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                " name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
            )
            done = {r["name"] for r in c.execute("SELECT name FROM schema_migrations").fetchall()}
            for f in files:
                if f.name in done:
                    continue
                with c.transaction():
                    c.execute(f.read_text())
                    c.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (f.name,))
                applied.append(f.name)
        finally:
            c.execute("SELECT pg_advisory_unlock(7420151)")
    return applied
