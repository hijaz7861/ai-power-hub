# AI POWER HUB — PROJECT STATUS

Last updated: 2026-11-09

## Current milestone: prepaid multi-turn AI, payments, recovery and customer privacy

### Implemented in feat/backend-foundation
- [x] FastAPI, SQLAlchemy and Alembic migrations through 0011
- [x] Registration/login, scrypt password hashing, short-lived bearer tokens and customer/admin roles
- [x] CLI-only bootstrap for an existing administrator account
- [x] Idempotent credit grants/debits, admin actor audit and customer-scoped credit ledger
- [x] Integer-safe wholesale-to-retail pricing engine and admin supplier-offer registry
- [x] HTTPS-only OpenAI-compatible async adapter with mocked HTTP tests
- [x] Customer account dashboard and HttpOnly SameSite=Strict session cookies
- [x] Same-origin validation for cookie-authenticated login, registration, logout, AI, payment, admin and conversation-delete mutations
- [x] Production frontend requires explicit APP_ORIGIN for same-origin mutation checks
- [x] Browser security headers: nosniff, frame denial, referrer policy, permissions policy, production HSTS and no-store API responses
- [x] Production backend rejects SQLite and requires PostgreSQL, Redis, a strong SECRET_KEY, DEBUG=false and public HTTPS PUBLIC_APP_URL
- [x] Sign-in/sign-out events refresh chat history and role-gated admin workspace
- [x] Safepay PKR top-up and signed-webhook settlement foundation
- [x] Idempotent payment success settlement and duplicate success protection, including after a refund
- [x] Verified partial/full Safepay refund events reverse purchased credits through negative ledger entries
- [x] Cumulative refund amount bounded by original payment; exact tracker, order reference, currency and full/partial state must match
- [x] If credits were already consumed before refund, balance can become negative and paid AI use remains blocked until replenished
- [x] Admin-only payment order/refund inbox and Safepay webhook event audit inbox
- [x] Credit reservation before metered AI calls, with idempotent reserve/capture/release
- [x] Customer chat completion API for OpenAI and Mistral-compatible endpoints
- [x] Public model catalogue exposes only models with configured server credentials and matching active PKR input/output rate offers
- [x] Customer chat panel with model selection, response rendering, credit accounting and conversation switching
- [x] Persistent customer-owned conversations and multi-turn provider context; history endpoints enforce ownership
- [x] Customer can delete an owned conversation; stored messages, cached responses and request-content fingerprints are erased while financial/audit rows remain
- [x] Conversation deletion is blocked while an AI request is processing
- [x] Authenticated account export endpoint and customer-facing JSON download for profile, credit ledger, payment orders, AI usage and stored conversations
- [x] Password-confirmed account closure, login revocation, identity anonymization and chat-content erasure; financial records retained
- [x] Account closure refuses non-zero credit balances, pending payments, active AI requests and unsettled credit reservations
- [x] Redis-backed distributed rate limits for login, registration, chat, top-ups and account closure; development-only in-memory fallback
- [x] Actual provider token usage is priced through the integer-safe retail pricing engine
- [x] Provider failures release the full hold; unused reservation is returned after settlement
- [x] Completed AI responses are persisted so client retries do not issue duplicate paid calls
- [x] Missing usage or usage above the authorized hold is marked reconciliation_required; funds remain held
- [x] Admin-only reconciliation and evidence-referenced settlement/release controls
- [x] Admin recovery inbox for processing requests older than ten minutes
- [x] Recovery links orphaned reservations by idempotency key; reserved funds remain held for human provider-usage reconciliation
- [x] Recovery never auto-releases a hold when a provider may have completed a billable request
- [x] Admin Console UI for supplier rates, contract attestation, AI reconciliation/recovery, exceptional hold release, payment orders/refunds and webhook audit
- [x] PostgreSQL 16 CI migration round-trip: upgrade 0001–0011, downgrade to base, then re-upgrade to head
- [x] Provider catalogue distinguishes available OpenAI/Mistral adapter code from integrations not implemented

### Latest verified GitHub Actions
- [x] Backend CI #564: 96 tests passed; SQLite migration validation passed
- [x] PostgreSQL migration job in Backend CI #564: PostgreSQL 16 upgrade, downgrade and re-upgrade passed
- [x] Frontend CI #299: TypeScript type check and Next.js production build passed
- [ ] Browser end-to-end test of registration, login, checkout, multi-turn chat, refund, export and deletion
- [ ] Termux-native install and runtime confirmed

### Remaining engineering and operational gates
- [ ] Safepay merchant-side reconciliation against provider tracker/report, refund execution, disputes and chargebacks
- [ ] Real Safepay sandbox transaction and signed webhook delivery
- [ ] Live OpenAI/Mistral provider calls and provider-side usage reconciliation
- [ ] Subscription plans, renewals, cancellation and plan enforcement
- [ ] PostgreSQL production rollout, backup/restore drills and connection-pool sizing
- [x] Route-specific rate limiting for authentication, chat, top-ups and account closure (Redis required in production)
- [ ] Additional abuse controls, request-size/time limits and centralized monitoring
- [ ] Email verification, password reset, token revocation/rotation and account recovery
- [ ] Anthropic/Gemini native adapters and image/audio/video integrations
- [ ] Opt-in contributor node agent, sandbox, quotas, work verification and payout settlement
- [ ] Independent security/privacy review, browser end-to-end tests, production deployment and monitoring
- [ ] Termux-native install and runtime verification

## Operational and commercial limitations
- OpenAI/Mistral calls are implemented but not verified with live provider credentials.
- Model execution requires server-side credentials and two matching active PKR supplier offers for input/output token rates.
- contract_status=verified is an administrator attestation based on an external signed agreement; software does not independently verify resale rights.
- If provider usage is missing or exceeds the authorized reservation, funds remain held for reconciliation. Admin settlement/release requires external evidence and administrator attestation.
- Safepay refund processing is based on signed webhook events and mocked CI tests; no merchant sandbox/live transaction has been executed.
- A refund can create a negative credit balance when credits have already been spent. This is an internal credit reversal, not an automated refund payout to the payer's bank/card.
- Production config fails closed unless PostgreSQL, Redis, strong SECRET_KEY, HTTPS PUBLIC_APP_URL and frontend APP_ORIGIN are configured. No production environment has yet been provisioned or deployed. Redis is mandatory for distributed production rate limiting; the in-memory limiter is development-only.
- Account export and account closure are implemented; closure anonymizes the login identity and erases app-stored chat content, but retains financial/audit metadata for reconciliation. It does not control provider-side retention or replace a legally reviewed privacy policy.
- No production deployment, live commercial service or revenue-generation claim is made.
- Keep PR #1 Draft/Open until live provider/payment checks, independent review and deployment gates are complete.
