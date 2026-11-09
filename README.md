# AI POWER HUB

**One Platform. All AI Capabilities.**

A modular multi-provider AI SaaS platform under active development. It is not yet a production-ready commercial service.

## Product direction

One workspace for AI chat and reasoning, image, video, audio, coding, education, research, document intelligence, agents and business automation. A capability is labelled operational only after its provider integration and end-to-end behavior are verified.

## Initial business model

The proposed entry plan starts at **PKR 100/month**. Usage is credit-metered; plans and limits must be set against verified provider and infrastructure costs. Unlimited expensive usage is not included.

## Implemented foundation

- FastAPI, SQLAlchemy and Alembic migrations through 0011.
- Customer registration/login and role-based admin authorization.
- Credit accounts, auditable ledger, idempotent grants/debits and customer-scoped history.
- Integer-minor-unit pricing engine and admin-managed supplier wholesale offers.
- OpenAI-compatible adapter and prepaid chat endpoint for OpenAI and Mistral.
- Customer-facing chat panel with model selection, persistent multi-turn history and conversation switching.
- Credit reservation before a provider call, actual-usage settlement and unused-credit release.
- Idempotent AI request records so a retry does not call the paid provider twice.
- Admin recovery inbox for stale AI executions; reserved holds remain held until provider-side usage is checked.
- Customer conversation deletion erases stored messages, cached response text and request-content fingerprints while preserving financial/audit rows.
- Authenticated account export download for profile, credit ledger, payment orders, AI usage and stored conversations.
- Password-confirmed account closure with login revocation, identity anonymization and stored chat-content erasure; financial/audit rows remain for reconciliation.
- Account closure is blocked while credit balances, payment orders, AI requests or reservations remain unsettled.
- Redis-backed distributed rate limits for login, registration, AI chat, top-ups and account closure; local development can use an in-memory fallback.
- Admin Console for supplier token rates, AI reconciliation/recovery, payment orders, cumulative refund totals and Safepay webhook event audit.
- Safepay top-up and signed-webhook settlement foundation.
- Verified partial/full Safepay refund webhook events reverse purchased credits with event idempotency and a bounded cumulative refund total.
- Same-origin validation for cookie-authenticated mutations and browser security headers.
- Production configuration fails closed unless PostgreSQL, Redis, a strong secret, public HTTPS URL and frontend APP_ORIGIN are configured.

## Enabling a metered chat model

The endpoint is POST /api/v1/chat/completions. It requires:
1. A server-side OPENAI_API_KEY or MISTRAL_API_KEY.
2. Two matching supplier offers for the exact provider/model: per_1k_input_tokens and per_1k_output_tokens.
3. Both offers must be active, PKR-denominated and have contract_status=verified.
4. An authenticated customer with enough credits for the maximum estimated request cost.

The public model catalogue lists only models with configured credentials and complete verified rate pairs. The verified contract state is an administrator assertion, not automatic legal verification. Do not activate an offer until supplier terms and resale rights have been checked externally.

Credits are reserved before the paid provider call. After a response with valid token usage, the platform calculates the retail charge, captures it and releases the unused reserve. A retry with the same idempotency key returns the stored completed response rather than issuing another paid request.

Conversation history is stored under the customer account. Customers can delete individual conversations; stored messages, cached response text and request-content fingerprints are removed, while financial/audit request metadata remains. The account export endpoint is GET /api/v1/account/export; the customer dashboard provides a download link. Account closure is POST /api/v1/account/close and requires password confirmation. Closure anonymizes the account email, disables login, erases stored conversations and cached response text, and retains payment/credit/usage audit records. It is blocked while the balance is non-zero or a payment, AI request or credit hold is unsettled. Provider-side retention is outside this application's control; a reviewed privacy and retention policy is still required.

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

SQLite is for local development and tests only. Production startup rejects SQLite and requires PostgreSQL, Redis (REDIS_URL), a random SECRET_KEY of at least 32 characters, DEBUG=false and a public HTTPS PUBLIC_APP_URL.

Install the optional PostgreSQL driver from requirements-postgres.txt and configure a SQLAlchemy URL such as:

```
postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
```

The backend CI includes a PostgreSQL 16 service that upgrades all migrations, downgrades to base and re-upgrades to head. This validates the migration chain against PostgreSQL; it is not a production backup/restore drill.

Sensitive routes use Redis-backed fixed-window rate limits in production. A process-local in-memory fallback is used only for development and is not suitable for multi-worker or multi-instance production. The limiter keys use the direct network peer and authenticated principal; forwarded IP headers are not trusted by the app.

The Next.js cookie-authenticated backend-for-frontend rejects cross-origin mutations. Set frontend APP_ORIGIN to the exact public origin (for example, https://ai.example.com) in production. Browser security headers include frame denial, MIME sniffing protection, referrer policy, restricted permissions, production HSTS and no-store API responses. Configure all secrets through the hosting provider's secret manager; never commit them.

## Verification and security

- Backend CI #564: 96 tests passed; SQLite migration validation passed.
- Backend CI #564 PostgreSQL 16 job: upgrade, downgrade and re-upgrade passed.
- Frontend CI #299: TypeScript check and Next.js production build passed.
- Live OpenAI/Mistral calls, Safepay sandbox transactions, browser end-to-end testing and production deployment have not been performed.
- Provider adapters and mocked CI tests do not establish live supplier access, resale rights, production readiness or revenue.
- A verified supplier contract state is an administrator attestation, not independent legal verification.

See PROJECT_STATUS.md for current verification gates.
