-- pgAdmin: Servers → PostgreSQL 18 → connect as postgres → Query Tool → Execute (F5)
-- If a line says "already exists", run the remaining lines only.

CREATE ROLE ledger WITH LOGIN PASSWORD 'ledger';
CREATE DATABASE warehouse_ledger OWNER ledger;
GRANT ALL PRIVILEGES ON DATABASE warehouse_ledger TO ledger;