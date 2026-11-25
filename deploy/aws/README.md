# AWS deploy (Warehouse Ledger)

Goal: public HTTPS URL, **RDS Postgres**, container on **App Runner**, GitHub Actions deploy.

You cannot skip the account. AWS will not give us an API without it.

## 1. Create the account (you)

1. Open https://portal.aws.amazon.com/billing/signup
2. Use your own email and a password manager password.
3. They will ask for a card even on the free tier. That is normal.
4. Choose **Basic support** (free).
5. Do **not** create access keys on the root user.
6. When the console loads, tell this chat: **account is ready**. Do not paste passwords or keys here.

## 2. After that (we do together)

1. IAM user with admin for this project (not root).
2. `aws configure` on this PC — you type the keys in the terminal, not in chat.
3. Create RDS Postgres + Redis + App Runner (API+UI) + worker service.
4. GitHub Actions: build `Dockerfile.aws`, push, deploy.
5. Point Paystack callback/webhook at the new URL.

Live public HTTPS is on the Rackzar VPS via GitHub Actions (`docs/DEPLOY.md`). Use this AWS path only on a standard personal account that can create RDS and a container service.
