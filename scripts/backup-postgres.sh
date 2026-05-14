#!/usr/bin/env bash
# Logical backup of the stakemind database via docker compose (postgres service).
# Usage (from repo root): ./scripts/backup-postgres.sh [output-file.sql]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
DEFAULT_OUT="${ROOT}/backups/postgres-$(date -u +%Y%m%dT%H%M%SZ).sql"
OUT="${1:-$DEFAULT_OUT}"
mkdir -p "$(dirname "$OUT")"
docker compose exec -T postgres pg_dump -U stakemind stakemind >"$OUT"
echo "Wrote ${OUT}"
