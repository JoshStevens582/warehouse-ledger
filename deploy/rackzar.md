# Optional VPS deploy (Rackzar)

**Warehouse Ledger is a portfolio project** — not part of Custom Chat and Automation.  
For job applications, the **GitHub repo + README** is enough. Deploy only if you want a public HTTPS demo (e.g. your own domain or a sslip.io name).

Atlas still owns **ports 80/443** on the VPS. Ledger runs on Docker network **cca-edge** like Counter, but you choose a **hostname that is not** `*.customchatandautomation.co.za` unless you explicitly want that.

## 1. Pick a hostname

Examples:

| Hostname | DNS |
| --- | --- |
| Your own domain (e.g. `ledger.yourname.dev`) | A → `102.203.81.249` |
| sslip.io (quick test) | Often `https://102-203-81-249.sslip.io` — use a **dedicated** Caddy `SITE_ADDRESS` block you add yourself; do not mix with CCA product subdomains |

Set Paystack **callback** and **webhook** to that HTTPS origin when you go live.

## 2. Clone and `.env` on the server

```bash
docker network create cca-edge   # skip if it exists
git clone https://github.com/JoshStevens582/warehouse-ledger.git /opt/ledger
cd /opt/ledger
cp .env.example .env
```

Edit `.env`:

- `JWT_SECRET` — strong random string
- Paystack test keys
- `CHECKOUT_CALLBACK_URL=https://YOUR-HOSTNAME/` (trailing slash)
- `CORS_ORIGINS=` empty (same-origin via Caddy)

## 3. Start Ledger (no public ports on web)

```bash
cd /opt/ledger
docker compose -f docker-compose.yml -f deploy/compose.edge.yml up -d --build
```

## 4. Caddy on the VPS

Append `deploy/caddy-edge.example.caddy` to **whatever Caddyfile already terminates HTTPS on that box** (usually Atlas `deploy/Caddyfile`), replacing `YOUR_HOSTNAME` with your chosen name. Rebuild that **web** container the same way you do for Counter/Clerk.

**Do not** add a `ledger.customchatandautomation.co.za` block unless you intentionally brand it as a CCA product.

## 5. Verify

```bash
curl -fsS https://YOUR-HOSTNAME/api/health
```

Demo users: `receiver@example.com` / `receiver123`, `picker@example.com` / `picker123`, `supervisor@example.com` / `supervisor123`.