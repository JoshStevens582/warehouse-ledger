# Demo script (≈2 minutes)

Use this in interviews or when recording a Loom. Open **pgAdmin** on `warehouse_ledger` → table **`orders`** in a second window.

## Prep

- API: `uv run uvicorn warehouse_ledger.main:app --host 127.0.0.1 --port 8080`
- UI: `cd frontend && npm run dev` → open the URL Vite prints (usually `http://localhost:5173`)
- Paystack test keys in `.env` (restart API after saving)

## Script

1. **Receiver** — `receiver@example.com` / `receiver123`  
   - Note **On shelf** for a SKU (e.g. `BOX-7A`).  
   - **Delivery (+)** with quantity 10.  
   - Say: *“Shelf count is not a column we edit; it is the sum of every row in `stock_movements`.”*

2. **Supervisor** — `supervisor@example.com` / `supervisor123`  
   - **1. Create order** (pick product + qty).  
   - Show new row in **`orders`**: `pending_payment`.  
   - **2. Pay with Paystack** → test card `4084084084084081`, CVV `408`, PIN `1234`, **Success**.  
   - Say: *“Paystack cannot hit localhost; in dev we record payment locally.”*  
   - **3. Record test payment** → **4. Refresh status** → `paid` in UI.  
   - Refresh pgAdmin **`orders`**: same `id`, **`status` = `paid`**, row in **`payments`**.

3. **Picker** — `picker@example.com` / `picker123`  
   - Create order or enter order # from step 2.  
   - **Pick (−)** for that order.  
   - Show **`stock_movements`** with negative `quantity_delta` and `order_id` set.

## API docs (no UI)

- Swagger: `http://127.0.0.1:8080/docs`  
- Health: `http://127.0.0.1:8080/api/health`

## One-liner for recruiters

*FastAPI warehouse ledger: append-only stock movements, JWT roles, Paystack checkout with signed webhooks and idempotent payments — Postgres is the source of truth.*