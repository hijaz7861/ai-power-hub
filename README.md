# AI POWER HUB

**One Platform. All AI Capabilities.**

A modular, multi-provider AI SaaS ecosystem. The repository is currently in its foundational backend phase; it is not yet a production-ready commercial service.

## Product scope

Planned categories include AI chat/reasoning, image, video, audio, coding, education, research, document intelligence, agents, and business automation. Each feature will be labelled according to its real implementation and provider status.

## Initial business model

The proposed entry plan starts at **PKR 100/month**. Credit limits and plan economics must be set from verified provider and infrastructure costs; unlimited expensive usage is not included.

## Current implementation

- FastAPI API foundation.
- SQLAlchemy user and credit data models.
- Registration, login, and bearer-token profile endpoint.
- Authenticated credit balance.
- Credit debit domain primitive with idempotency protection.
- Provider configuration catalogue with explicit non-operational status until a live call is verified.
- HTTPS-only OpenAI-compatible async adapter with mocked HTTP tests; no live supplier credentials are included.
- Admin role protection and a CLI-only bootstrap command for promoting an existing account.
- Admin-only supplier wholesale-offer registry, commercial-contract activation gate, and retail-price preview using the integer-safe pricing engine.
- Alembic initial database migration.
- Automated backend tests and GitHub Actions workflow.

## Local development

Python 3.11+ is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Set a long random SECRET_KEY in .env before using authentication.
python -m alembic upgrade head
python -m uvicorn backend.app.main:app --reload
```

API documentation is available at `/docs` while the local server is running.

Run tests:

```bash
python -m pytest -q
```

## Database

SQLite is for local development and tests. Production must use PostgreSQL and run Alembic migrations before application startup.

For PostgreSQL, install the optional driver from `requirements-postgres.txt` and configure a SQLAlchemy URL such as `postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME`.

```bash
python -m alembic upgrade head
```

## Security

- Never commit real API keys, passwords, tokens, database credentials, or production secrets.
- Keep `.env` out of Git.
- Use a cryptographically random `SECRET_KEY` of at least 32 characters in production.
- Production schema changes must use reviewed migrations.
- Provider integrations are not considered operational until live credentials, calls, cost accounting, and tests are verified.

## Status

**Current phase:** Backend foundation, first domain primitives, and initial frontend dashboard.

**Not yet implemented:** verified live supplier/API calls and resale agreements, payment gateway and credit purchase settlement, subscription enforcement, customer-facing chat execution, frontend authentication, email verification, password recovery, rate limiting, PostgreSQL production rollout, production deployment, and operational monitoring.

Only verified functionality will be marked operational.
