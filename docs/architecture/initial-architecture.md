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
- Provider configuration catalogue that explicitly reports adapters as not implemented.
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
- GET /api/v1/providers

## Database and migrations

- SQLite is intended only for local development and tests.
- Production must use PostgreSQL and the optional psycopg driver.
- Run `python -m alembic upgrade head` before production application startup.
- Automatic `create_all` is disabled when APP_ENV=production.

## Important limitations

- Provider adapters do not call external AI services yet.
- No credit purchase or grant endpoint is exposed.
- Payment processing and subscription enforcement are not implemented.
- Credit debit is not yet connected to AI request execution.
- Rate limiting, email verification, password reset, refresh-token rotation, and administrative RBAC remain future work.
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
