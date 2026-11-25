# Deploy (phase 2)

**Live demo:** https://ledger.102-203-81-249.sslip.io

Pushes to `main` run pytest + Playwright, then GitHub Actions SSHs to the Rackzar VPS, resets `/opt/ledger` to `origin/main`, and rebuilds Docker Compose. Manual steps: [deploy/rackzar.md](../deploy/rackzar.md).

Repo secrets (set once, never commit): `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`.

## What you need

| Piece | Notes |
| --- | --- |
| PostgreSQL | Managed DB (Render, Railway, Supabase, etc.) |
| API | `Dockerfile` in repo root; run `alembic upgrade head` then uvicorn |
| Redis | Required only if you demo **ARQ receipt** emails |
| Static UI | `cd frontend && npm run build`; serve `dist/` behind same host or CDN |
| Secrets | `JWT_SECRET`, `PAYSTACK_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `CHECKOUT_CALLBACK_URL` |

## Paystack (test mode is fine)

1. Set **callback URL** to your UI origin, e.g. `https://your-app.example/` (must match `CHECKOUT_CALLBACK_URL`).
2. Set **webhook URL** to `https://your-api.example/api/paystack/webhook` (exact path from `main.py`).
3. Use the webhook secret Paystack shows → `PAYSTACK_WEBHOOK_SECRET` in hosting env.

In production-like hosting, **charge.success** webhooks mark orders paid; you do not need **Confirm payment** in the UI for happy path.

## Minimal checklist

1. Create DB; run migrations once.
2. Deploy API with env from `.env.example` (no secrets in git).
3. Point frontend `Vite` proxy or build-time API base at the API URL; enable CORS for the UI origin if split hosts.
4. Smoke: `GET /api/health`, login supervisor, create order → checkout → Paystack test card → webhook → `paid`.

## Docker Compose (VPS)

On a small VPS, `docker compose up` runs Postgres, Redis, API, and worker. Terminate TLS with Caddy or nginx in front of port 8080 and your static UI.

Do not commit `.env`. Set Paystack and JWT values in the host’s secret store only.