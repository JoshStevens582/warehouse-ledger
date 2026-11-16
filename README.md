# Warehouse Ledger

[![CI](https://github.com/JoshStevens582/warehouse-ledger/actions/workflows/ci.yml/badge.svg)](https://github.com/JoshStevens582/warehouse-ledger/actions/workflows/ci.yml)

Full-stack warehouse demo: **append-only stock movements** in PostgreSQL, **JWT roles**, and **Paystack** checkout with signed webhooks. Built to show backend Python practices recruiters care about (tests, types, migrations, payment idempotency).

## Problem

Warehouses need a trustworthy shelf count. This app **never stores “on shelf” as an editable number**. Every delivery and pick is one row in `stock_movements`; the API reports shelf quantity as **`SUM(quantity_delta)`**. Orders and payments live in their own tables so money and inventory stay auditable.

## Screenshots

After one run of [docs/DEMO.md](docs/DEMO.md), add PNGs to `docs/images/` (capture guide in [docs/images/README.md](docs/images/README.md)):

- `receiver-shelf.png` — shelf table + delivery
- `supervisor-paid.png` — order status **paid** in the UI
- `pgadmin-orders.png` — `orders.status = paid` in pgAdmin

Then uncomment the image row in this README (search for `receiver-shelf.png`).

## Stack

- **Python:** FastAPI, SQLAlchemy 2, Alembic, Pydantic
- **DB:** PostgreSQL (ledger + orders + payments)
- **Auth:** JWT, roles `receiver` | `picker` | `supervisor`
- **Payments:** Paystack initialize, HMAC webhooks, idempotent `payments` rows
- **Async jobs:** ARQ + Redis (receipt delivery after payment)
- **UI:** React (Vite) — thin client over `/api`
- **Quality:** pytest (branch coverage), Ruff, Mypy, GitHub Actions

## Quick start

**Windows (local Postgres on 5432):**

1. Run `scripts/init_local_postgres.sql` once in pgAdmin.
2. `copy .env.example .env` — set Paystack **test** keys; set `CHECKOUT_CALLBACK_URL` to your Vite URL (e.g. `http://localhost:5173/`).
3. From this folder:

```bash
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn warehouse_ledger.main:app --host 127.0.0.1 --port 8080
```

4. UI: `cd frontend && npm install && npm run dev`

| Role | Email | Password |
| --- | --- | --- |
| Receiver | receiver@example.com | receiver123 |
| Picker | picker@example.com | picker123 |
| Supervisor | supervisor@example.com | supervisor123 |

**API docs:** [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)  
**Health:** `GET /api/health` (includes DB name + movement row count)

Docker and Redis notes: see comments in `.env.example` and `docker-compose.yml`.

## Demo for interviews

Step-by-step script: **[docs/DEMO.md](docs/DEMO.md)** (~2 minutes).

**30-second version:**

1. Movements are append-only; shelf total is a SQL sum.
2. Roles enforce who can deliver vs pick vs manage orders.
3. Order → Paystack reference → webhook verifies HMAC → one payment row; duplicate events ignored.
4. Local dev uses **Record test payment** when Paystack cannot reach localhost.

## Tests

```bash
uv run ruff check .
uv run mypy src
uv run pytest --cov=warehouse_ledger --cov-branch
```

CI runs the same on push (Postgres + Redis service containers). Prefer a dedicated `warehouse_ledger_test` database so pytest does not wipe your play data — see `.env.example`.

## CV copy-paste

Ready-made bullets: **[docs/CV-BULLETS.md](docs/CV-BULLETS.md)**

## Project layout

| Path | Purpose |
| --- | --- |
| `src/warehouse_ledger/` | API, models, Paystack, services |
| `alembic/` | Migrations |
| `tests/` | pytest (roles, webhooks, record-test-payment) |
| `frontend/` | Vite React UI |
| `scripts/` | Postgres init, Paystack webhook relay (local dev) |