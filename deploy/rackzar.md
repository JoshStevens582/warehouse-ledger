# Warehouse Ledger on Rackzar (same VPS as Atlas)

Atlas Caddy terminates HTTPS on **ledger.customchatandautomation.co.za**. Ledger containers join **cca-edge** (same pattern as Counter and Clerk).

## DNS (once)

`ledger.customchatandautomation.co.za` **A** → `102.203.81.249`

## Paystack (test or live)

- **Callback URL:** `https://ledger.customchatandautomation.co.za/`
- **Webhook URL:** `https://ledger.customchatandautomation.co.za/api/webhooks/paystack`

## Server: clone and env

```bash
docker network create cca-edge   # skip if it already exists
git clone https://github.com/JoshStevens582/warehouse-ledger.git /opt/ledger
cd /opt/ledger
cp .env.example .env
```

Set in `.env` (never commit):

- `JWT_SECRET` — long random string
- `PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY`
- `CHECKOUT_CALLBACK_URL=https://ledger.customchatandautomation.co.za/`
- `CORS_ORIGINS=` (empty — same-origin via Caddy)

## Start Ledger

```bash
cd /opt/ledger
docker compose -f docker-compose.yml -f deploy/compose.edge.yml up -d --build
```

Containers: `ledger-db`, `ledger-redis`, `ledger-api`, `ledger-worker`, `ledger-web` (no public ports).

## Atlas Caddy

Merge `deploy/caddy-atlas-ledger.caddy` into `/opt/atlas/deploy/Caddyfile`, then:

```bash
cd /opt/atlas && git pull && docker compose -f docker-compose.yml -f deploy/compose.counter-edge.yml up -d --build web
```

(Use the same edge overlay file you already use for Counter/Clerk if the filename differs.)

## Verify

```bash
curl -fsS https://ledger.customchatandautomation.co.za/api/health
curl -fsS https://ledger.customchatandautomation.co.za/ | grep -q 'id="root"'
```

Demo logins: `receiver@example.com` / `receiver123`, `picker@example.com` / `picker123`, `supervisor@example.com` / `supervisor123`.