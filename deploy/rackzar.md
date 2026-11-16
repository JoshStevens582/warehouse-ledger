# Deploy on Rackzar (portfolio — not CCA)

**Live URL:** `https://ledger.102-203-81-249.sslip.io`  
(sslip.io points at your VPS IP — no Custom Chat domain.)

SSH to the VPS, then run the blocks below in order.

## 1. Ledger app

```bash
docker network create cca-edge 2>/dev/null || true
test -d /opt/ledger || git clone https://github.com/JoshStevens582/warehouse-ledger.git /opt/ledger
cd /opt/ledger && git pull
```

If `/opt/ledger/.env` does not exist yet:

```bash
cp .env.example .env
nano .env
```

Set:

- `JWT_SECRET` — long random string
- `PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY`
- `CHECKOUT_CALLBACK_URL=https://ledger.102-203-81-249.sslip.io/`
- `CORS_ORIGINS=` (empty)

Start:

```bash
cd /opt/ledger
docker compose -f docker-compose.yml -f deploy/compose.edge.yml up -d --build
docker ps --filter name=ledger
```

## 2. Caddy (Atlas still owns :443)

Append the file `deploy/caddy-ledger-portfolio.caddy` to `/opt/atlas/deploy/Caddyfile` (or paste its contents once at the end of that file).

```bash
cd /opt/atlas
git pull || true
# If the ledger block is missing from Caddyfile, append it:
grep -q 'ledger.102-203-81-249.sslip.io' deploy/Caddyfile || cat /opt/ledger/deploy/caddy-ledger-portfolio.caddy >> deploy/Caddyfile
docker compose -f docker-compose.yml -f deploy/compose.counter-edge.yml up -d --build web
```

## 3. Paystack (test keys)

- Callback: `https://ledger.102-203-81-249.sslip.io/`
- Webhook: `https://ledger.102-203-81-249.sslip.io/api/webhooks/paystack`

## 4. Verify

```bash
curl -fsS https://ledger.102-203-81-249.sslip.io/api/health
```

Browser: `https://ledger.102-203-81-249.sslip.io` — `supervisor@example.com` / `supervisor123`

## CV line (optional)

Portfolio demo: `https://ledger.102-203-81-249.sslip.io` — GitHub: `github.com/JoshStevens582/warehouse-ledger`