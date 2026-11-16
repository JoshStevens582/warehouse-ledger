# CV / LinkedIn bullets (Python backend)

Paste 2–4 of these under Projects. Link the **GitHub repo** in the header line.

**Project line (title + link)**  
`Warehouse Ledger` — [github.com/…/warehouse-ledger](https://github.com/) *(replace with your URL)*

**Bullets (pick what fits your CV length)**

- Built a **FastAPI** warehouse API with **SQLAlchemy 2**, **Alembic**, and **PostgreSQL**; on-shelf quantity is **`SUM(quantity_delta)`** over append-only **`stock_movements`**, not a mutable stock column.

- Implemented **JWT authentication** and **role-based access** (receiver / picker / supervisor), including business rules such as blocking picks when stock is insufficient.

- Integrated **Paystack** (transaction initialize + **HMAC-SHA512** webhook verification), **idempotent** payment rows, and a dev-only endpoint to simulate webhooks on localhost.

- Wrote **pytest** tests with branch coverage for webhooks, payments, and role boundaries; enforced quality with **Ruff**, **Mypy**, and **GitHub Actions** CI (Postgres + Redis services).

- Delivered a thin **React (Vite)** client for demos; API documented via **OpenAPI** (`/docs`).

**Skills line (optional)**  
Python · FastAPI · SQLAlchemy · PostgreSQL · Alembic · pytest · Paystack · JWT · Redis/ARQ

**Interview hook (spoken, 20 s)**  
“We never store ‘qty on shelf’ as a field we trust. Every delivery and pick is an immutable movement row; the API sums them. Orders and Paystack payments are separate tables, and webhooks are verified and idempotent.”