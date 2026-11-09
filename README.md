# AI POWER HUB

**One Platform. All AI Capabilities.**

A modular multi-provider AI SaaS platform under active development. It is not yet a production-ready commercial service.

## Product direction

One workspace for AI chat and reasoning, image, video, audio, coding, education, research, document intelligence, agents and business automation. A capability is labelled operational only after its provider integration and end-to-end behavior are verified.

## Initial business model

The proposed entry plan starts at **PKR 100/month**. Usage is credit-metered; plans and limits must be set against verified provider and infrastructure costs. Unlimited expensive usage is not included.

## Implemented foundation

- FastAPI, SQLAlchemy and Alembic migrations through 0009.
- Customer registration/login and role-based admin authorization.
- Credit accounts, auditable ledger, idempotent grants/debits and customer-scoped history.
- Integer-minor-unit pricing engine and admin-managed supplier wholesale offers.
- OpenAI-compatible async adapter and prepaid chat endpoint for OpenAI and Mistral.
- Customer-facing chat panel with verified model catalogue, multi-turn conversation history and conversation switching.
- Credit reservation before a provider call, actual-usage settlement and unused-credit release.
- Idempotent AI request records so a retry does not call the paid provider twice.
- Admin Console for supplier token rates, reconciliation inbox, evidence-referenced settlement and exceptional hold release.
- Safepay top-up and signed-webhook settlement foundation (mock-tested only).
- Next.js customer account panel and server-managed HttpOnly session cookies.

## Enabling a metered chat model

The endpoint is POST /api/v1/chat/completions. It requires:
1. A server-side OPENAI_API_KEY or MISTRAL_API_KEY.
2. Two matching supplier offers for the exact provider/model: per_1k_input_tokens and per_1k_output_tokens.
3. Both offers must be active, PKR-denominated and have contract_status=verified.
4. An authenticated customer with enough credits for the maximum estimated request cost.

The public model catalogue lists only models with configured credentials and complete verified rate pairs. The verified contract state is an administrator assertion, not automatic legal verification. Do not activate an offer until supplier terms and resale rights have been checked externally.

Credits are reserved before the paid provider call. After a response with valid token usage, the platform calculates the retail charge, captures it and releases the unused reserve. A retry with the same idempotency key returns the stored completed response rather than issuing another paid request.

Conversation history is stored under the customer account. The API checks ownership before returning a thread and includes prior turns in subsequent provider requests. Customer retention/export/deletion controls and a published privacy policy remain to be implemented.

If token usage is missing or exceeds the authorized reserve, the request is marked reconciliation_required and the hold remains in place. An admin-only inbox and evidence-referenced reconciliation/hold-release controls are available; evidence is an administrator attestation and must be checked externally.

## Local development

Python 3.11+ is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Set a cryptographically random SECRET_KEY before using authentication.
python -m alembic upgrade head
python -m uvicorn backend.app.main:app --reload
```

API documentation is available at /docs.

Run tests:

```bash
python -m pytest -q
```

## Database

SQLite is for local development and tests. Production must use PostgreSQL, run Alembic migrations before application startup, and validate backups/restores.

Install the optional PostgreSQL driver from requirements-postgres.txt and configure a SQLAlchemy URL such as:

```
postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
```

## Verification and security

- Latest Backend CI #393: 72 tests passed; migrations 0001–0009 passed.
- Latest Frontend CI #179: TypeScript and production build passed.
- Never commit real API keys, passwords, tokens, database credentials or production secrets.
- Keep .env out of Git. Configure provider credentials on the backend only.
- Use a random SECRET_KEY of at least 32 characters in production.
- Do not trust a browser redirect as payment confirmation; Safepay credits are granted only by the signed, matching webhook.
- Provider adapters and mocked CI tests do not establish live supplier access, resale rights, production readiness or revenue.
- No production deployment or live payment/provider transaction has been verified.

See PROJECT_STATUS.md for current verification gates.
