# AI Power Hub — Initial Architecture

## Implemented in this branch

- FastAPI application and liveness/readiness endpoints.
- SQLAlchemy persistence models for users, credit accounts, and credit ledger.
- Environment-backed settings with production checks for secret strength and debug mode.
- Password hashing using Python scrypt.
- Short-lived HS256 bearer access tokens.
- Registration, login, and authenticated profile endpoint.
- Authenticated credit-balance endpoint.
- Integer-credit debit service with conditional balance update and idempotency key.
- Provider configuration catalogue that explicitly reports integrations as non-operational until verified.
- HTTPS-only async OpenAI-compatible provider adapter with mocked transport tests.
- Administrator role authorization and CLI-only bootstrap for an existing account.
- Admin-only supplier wholesale-offer registry, commercial contract activation gate, and retail-price quote preview.
- Alembic migration environment and initial schema migration.
- Isolated SQLite tests and GitHub Actions CI.

## Current API

- GET /
- GET /health
- GET /ready
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- GET /api/v1/auth/me (Bearer token)
- GET /api/v1/credits/balance (Bearer token)
- GET /api/v1/credits/ledger (Bearer token; current-user scoped)
- GET /api/v1/providers
- GET /api/v1/admin/supplier-offers (administrator)
- POST /api/v1/admin/supplier-offers (administrator)
- POST /api/v1/admin/supplier-offers/{offer_id}/quote (administrator)
- POST /api/v1/admin/credits/grant (administrator; audited manual adjustment)
- POST /api/v1/webhooks/safepay (public signed provider webhook inbox)
- GET /api/v1/admin/payment-events (administrator)

## Database and migrations

- SQLite is intended only for local development and tests.
- Production must use PostgreSQL and the optional psycopg driver.
- Run `python -m alembic upgrade head` before production application startup.
- Automatic `create_all` is disabled when APP_ENV=production.

## Important limitations

- The provider adapter is implemented and mock-tested, but no live external AI service call or supplier resale agreement has been verified.
- Safepay webhook ingestion verifies raw-body HMAC-SHA512 signatures and deduplicates events, but payment order creation, reconciliation and credit settlement are not implemented.
- No credit purchase or grant endpoint is exposed.
- Payment processing and subscription enforcement are not implemented.
- Credit debit and manual grant primitives are not yet connected to metered AI request execution or verified customer payments.
- Advanced RBAC, administrator management UI, rate limiting, email verification, password reset, refresh-token rotation, and browser end-to-end tests remain future work.
- No production deployment or production security audit has been completed.

## Local development

```bash
python -m pip install -r requirements.txt
cp .env.example .env
python -m alembic upgrade head
python -m uvicorn backend.app.main:app --reload
python -m pytest -q
```

Set a strong, random SECRET_KEY before deployment. Never commit real credentials.
