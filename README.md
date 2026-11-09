# AI POWER HUB

**One Platform. All AI Capabilities.**

A modular multi-provider AI SaaS platform under active development. It is not yet a production-ready commercial service.

## Product direction

One workspace for AI chat and reasoning, image, video, audio, coding, education, research, document intelligence, agents and business automation. A capability is labelled operational only after its provider integration and end-to-end behavior are verified.

## Initial business model

The proposed entry plan starts at **PKR 100/month**. Usage is credit-metered; plans and limits must be set against verified provider and infrastructure costs. Unlimited expensive usage is not included.

## Implemented foundation

- FastAPI, SQLAlchemy and Alembic migrations through 0010.
- Customer registration/login and role-based admin authorization.
- Credit accounts, auditable ledger, idempotent grants/debits and customer-scoped history.
- Integer-minor-unit pricing engine and admin-managed supplier wholesale offers.
- OpenAI-compatible async adapter and prepaid chat endpoint for OpenAI and Mistral.
- Customer-facing chat panel with verified model catalogue, multi-turn conversation history and conversation switching.
- Credit reservation before a provider call, actual-usage settlement and unused-credit release.
- Idempotent AI request records so a retry does not call the paid provider twice.
- Admin recovery inbox for stale AI executions; a reserved hold remains held until provider-side usage is checked.
- Customer conversation deletion erases stored messages and cached response text while preserving financial/audit request rows.
- Admin Console for supplier token rates, AI reconciliation, payment orders, cumulative refund totals and Safepay webhook event audit.
- Safepay top-up and signed-webhook settlement foundation.
- Verified partial/full Safepay refund webhook events reverse purchased credits with event idempotency and a bounded cumulative refund total.
- Same-origin checks on cookie-authenticated mutation routes.
- Next.js customer account panel and server-managed HttpOnly session cookies.

## Enabling a metered chat model

The endpoint is POST /api/v1/chat/completions. It requires:
1. A server-side OPENAI_API_KEY or MISTRAL_API_KEY.
2. Two matching supplier offers for the exact provider/model: per_1k_input_tokens and per_1k_output_tokens.
3. Both offers must be active, PKR-denominated and have contract_status=verified.
4. An authenticated customer with enough credits for the maximum estimated request cost.

The public model catalogue lists only models with configured credentials and complete verified rate pairs. The verified contract state is an administrator assertion, not automatic legal verification. Do not activate an offer until supplier terms and resale rights have been checked externally.

Credits are reserved before the paid provider call. After a response with valid token usage, the platform calculates the retail charge, captures it and releases the unused reserve. A retry with the same idempotency key returns the stored completed response rather than issuing another paid request.

Conversation history is stored under the customer account. The API checks ownership before returning a thread and includes prior turns in subsequent provider requests. Customers can delete individual conversations; this removes stored message text and cached response text but retains financial/audit request metadata. Full account export/closure and a published privacy policy remain to be implemented.

## Safepay refund accounting

Only a signed, matching webhook can trigger credit reversal. A refund must match the original payment's tracker, order reference, currency and accepted provider tracker state. Duplicate event tokens are idempotent, and cumulative refunds cannot exceed the original top-up. If the credits were already consumed, the credit balance may become negative; paid AI usage is then blocked until the balance is replenished.

This is an internal credit-ledger reversal. It does not initiate or prove that Safepay has paid money back to the customer's bank/card. Merchant-side refund execution, settlement reports and chargeback dispute handling still require live provider integration and reconciliation.

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

## Database and production configuration

SQLite is for local development and tests only. Production startup rejects SQLite and requires PostgreSQL, a random SECRET_KEY of at least 32 characters, DEBUG=false, and a public HTTPS PUBLIC_APP_URL.

Install the optional PostgreSQL driver from requirements-postgres.txt and configure a SQLAlchemy URL such as:

```
postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
```

The Next.js cookie-authenticated backend-for-frontend rejects cross-origin mutations. Set frontend APP_ORIGIN to the exact public origin (for example, https://ai.example.com) in production. Do not commit secrets or paste them into chat; configure them through the hosting provider's secret manager.

## Verification and security

- Backend CI #499: 85 tests passed; Alembic migrations 0001–0010 passed.
- Frontend CI #259: TypeScript check and Next.js production build passed.
- Live OpenAI/Mistral calls, Safepay sandbox transactions, browser end-to-end testing and production deployment have not been performed.
- Provider adapters and mocked CI tests do not establish live supplier access, resale rights, production readiness or revenue.
- A verified supplier contract state is an administrator attestation, not independent legal verification.

See PROJECT_STATUS.md for current verification gates.
