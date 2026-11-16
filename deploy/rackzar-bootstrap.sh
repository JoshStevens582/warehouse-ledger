#!/bin/sh
# Run on the Rackzar VPS (browser console or SSH). Portfolio host — not CCA.
set -e

HOST="ledger.102-203-81-249.sslip.io"
LEDGER="/opt/ledger"
ATLAS="/opt/atlas"

echo "=== Warehouse Ledger deploy (sslip) ==="

docker network create cca-edge 2>/dev/null || true

if [ -d "$LEDGER/.git" ]; then
  git -C "$LEDGER" pull origin main
else
  git clone https://github.com/JoshStevens582/warehouse-ledger.git "$LEDGER"
fi

if [ ! -f "$LEDGER/.env" ]; then
  cp "$LEDGER/.env.example" "$LEDGER/.env"
  echo ""
  echo "STOP: Edit secrets, then run this script again:"
  echo "  nano $LEDGER/.env"
  echo "Set JWT_SECRET, PAYSTACK_SECRET_KEY, PAYSTACK_PUBLIC_KEY,"
  echo "CHECKOUT_CALLBACK_URL=https://${HOST}/"
  echo "Leave CORS_ORIGINS empty."
  exit 1
fi

if ! grep -q '^JWT_SECRET=.' "$LEDGER/.env" || grep -q 'change-me-in-production' "$LEDGER/.env"; then
  echo "STOP: Set JWT_SECRET in $LEDGER/.env (nano), then re-run this script."
  exit 1
fi

cd "$LEDGER"
docker compose -f docker-compose.yml -f deploy/compose.edge.yml up -d --build

if [ ! -d "$ATLAS/deploy" ]; then
  echo "STOP: $ATLAS not found — Atlas must already be on this VPS."
  exit 1
fi

grep -q "$HOST" "$ATLAS/deploy/Caddyfile" || \
  cat "$LEDGER/deploy/caddy-ledger-portfolio.caddy" >> "$ATLAS/deploy/Caddyfile"

cd "$ATLAS"
docker compose -f docker-compose.yml -f deploy/compose.counter-edge.yml up -d --build web

echo ""
echo "=== Done. Test: ==="
curl -fsS "https://${HOST}/api/health" || true
echo ""
echo "Open in browser: https://${HOST}"
echo "Supervisor demo: supervisor@example.com / supervisor123"