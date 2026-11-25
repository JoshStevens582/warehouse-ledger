#!/bin/sh
# Rebuild Ledger on this VPS. GitHub Actions already reset /opt/ledger to origin/main.
set -eu
LEDGER_ROOT="${LEDGER_ROOT:-/opt/ledger}"
cd "$LEDGER_ROOT"
test -f .env
docker network inspect cca-edge >/dev/null 2>&1 || docker network create cca-edge
docker compose -f docker-compose.yml -f deploy/compose.edge.yml up -d --build
curl -fsS --retry 8 --retry-delay 3 --retry-all-errors \
  https://ledger.102-203-81-249.sslip.io/api/health
