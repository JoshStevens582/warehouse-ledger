# README screenshots

| File | Content |
| --- | --- |
| `receiver-shelf.png` | Receiver — inventory table + activity |
| `supervisor-paid.png` | Supervisor — paid order workflow |
| `pgadmin-orders.png` | Order record panel (same fields as `orders` in Postgres) |

```powershell
# From repo root (API + Vite running on 5173)
powershell -File scripts/prepare_readme_screenshots.ps1
node scripts/capture-screenshots.mjs
```