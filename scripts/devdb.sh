#!/usr/bin/env bash
# Local Postgres 16 for Afterparty development, in Docker.
#   scripts/devdb.sh start | stop | reset
set -euo pipefail
NAME=afterparty-pg
PORT=54329
PSQL=(docker exec -i "$NAME" psql -U postgres -v ON_ERROR_STOP=1 -qtA)

wait_ready() {
  for _ in $(seq 1 30); do
    docker exec "$NAME" pg_isready -U postgres >/dev/null 2>&1 && return 0
    sleep 1
  done
  echo "postgres did not start" >&2
  return 1
}

ensure_dbs() {
  for db in afterparty afterparty_test; do
    "${PSQL[@]}" -c "SELECT 1 FROM pg_database WHERE datname='$db'" | grep -q 1 \
      || "${PSQL[@]}" -c "CREATE DATABASE $db"
  done
}

case "${1:-start}" in
  start)
    if ! docker ps -a --format '{{.Names}}' | grep -qx "$NAME"; then
      docker run -d --name "$NAME" -p "127.0.0.1:$PORT:5432" \
        -e POSTGRES_HOST_AUTH_METHOD=trust -v afterparty-pg:/var/lib/postgresql/data \
        postgres:16-alpine >/dev/null
    else
      docker start "$NAME" >/dev/null
    fi
    wait_ready
    ensure_dbs
    echo "postgres on 127.0.0.1:$PORT (databases: afterparty, afterparty_test; user postgres)"
    ;;
  stop) docker stop "$NAME" >/dev/null && echo stopped ;;
  reset)
    "$0" start >/dev/null
    for db in afterparty afterparty_test; do
      "${PSQL[@]}" -c "DROP DATABASE IF EXISTS $db WITH (FORCE)"
    done
    ensure_dbs
    echo reset
    ;;
esac
