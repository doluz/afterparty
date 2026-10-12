#!/usr/bin/env bash
# Build the web app into src/afterparty/static, where the API serves it.
set -euo pipefail
cd "$(dirname "$0")/.."
npm --prefix web ci --no-audit --no-fund
npm --prefix web run build
