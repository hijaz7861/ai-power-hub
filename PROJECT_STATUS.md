# AI POWER HUB — PROJECT STATUS

Last updated: 2026-11-09

## Current milestone: prepaid multi-turn AI, payment accounting and privacy controls

### Implemented in feat/backend-foundation
- [x] FastAPI, SQLAlchemy and Alembic migrations through 0010
- [x] Registration/login, scrypt password hashing, short-lived bearer tokens and customer/admin roles
- [x] CLI-only bootstrap for an existing administrator account
- [x] Idempotent credit grants/debits, admin actor audit and customer-scoped credit ledger
- [x] Integer-safe wholesale-to-retail pricing engine and admin supplier-offer registry
- [x] HTTPS-only OpenAI-compatible async adapter with mocked HTTP tests
- [x] Customer account dashboard and HttpOnly SameSite=Strict session cookies
- [x] Sign-in/sign-out events refresh chat history and role-gated admin workspace
- [x] Safepay PKR top-up and signed-webhook settlement foundation
- [x] Idempotent payment success settlement and duplicate success protection, including after a refund
- [x] Verified partial/full Safepay refund events reverse purchased credits through negative ledger entries
- [x] Cumulative refund amount bounded by the original payment; refunds require exact tracker, order reference, currency and accepted tracker state
- [x] If credits were already consumed before refund, balance can become negative and paid AI use remains blocked until replenished
- [x] Admin-only payment order and cumulative refund inbox
- [x] Admin-only Safepay webhook event audit inbox
- [x] Credit reservation before metered AI calls, with idempotent reserve/capture/release
- [x] Customer chat completion API for OpenAI and Mistral-compatible endpoints
- [x] Public model catalogue exposes only models with configured server credentials and matching active, PKR, contract-verified input/output rate offers
- [x] Customer-facing chat panel with model selection, response rendering, credit accounting and conversation switching
- [x] Persistent customer-owned conversations and multi-turn provider context
- [x] Conversation history endpoints enforce account ownership
- [x] Customer can delete an owned conversation; stored messages and cached response text are erased while financial/audit request rows remain
- [x] Conversation deletion is blocked while an AI request is processing
- [x] Actual provider token usage is priced through the integer-safe retail pricing engine
- [x] Provider failures release the full hold; unused reservation is returned after settlement
- [x] Completed AI responses are persisted so client retries do not issue duplicate paid calls
- [x] Missing usage or usage above the authorized hold is marked reconciliation_required; funds remain held
- [x] Admin-only reconciliation inbox and evidence-referenced settlement endpoint; release ledger entries identify the admin actor
- [x] Admin Console UI for supplier rates, contract attestation, AI reconciliation, exceptional hold release, payment orders/refunds and Safepay webhook audit
- [x] Provider catalogue distinguishes available OpenAI/Mistral adapter code from integrations not implemented

### Latest CI status
- [x] Previously verified Backend CI #402: 72 tests; migrations 0001–0009
- [x] Previously verified Frontend CI #197: TypeScript and production build
- [ ] Backend CI #449: includes migration 0010, refund accounting and conversation deletion tests; latest run is in progress
- [ ] Frontend CI #219: includes payment order inbox and conversation deletion UI; latest run is queued
- [ ] Browser end-to-end test of registration, login, checkout, multi-turn chat, refund and deletion

### Remaining engineering and operational gates
- [ ] Safe automated recovery workflow for interrupted in-progress AI requests; must never auto-release a hold if the provider may have completed a billable call
- [ ] Full account export and account closure/data-erasure workflow, with lawful financial/audit retention policy
- [ ] Safepay merchant-side reconciliation against provider tracker/report, refund disputes and chargebacks
- [ ] Real Safepay sandbox transaction and signed webhook delivery
- [ ] Live OpenAI/Mistral provider calls and provider-side usage reconciliation
- [ ] Subscription plans, renewals, cancellation and plan enforcement
- [ ] PostgreSQL production rollout, backup/restore drills and connection-pool sizing
- [ ] Rate limiting, abuse controls, CSRF/origin protection, request-size/time limits and security headers
- [ ] Email verification, password reset, token revocation/rotation and account recovery
- [ ] Anthropic/Gemini native adapters and image/audio/video integrations
- [ ] Opt-in contributor node agent, sandbox, quotas, work verification and payout settlement
- [ ] Security/privacy review, end-to-end tests, production deployment and monitoring
- [ ] Termux-native install and runtime verification

## Operational and commercial limitations
- OpenAI/Mistral calls are implemented but not verified with live provider credentials.
- Model execution requires server-side credentials and two matching active PKR supplier offers for input/output token rates.
- contract_status=verified is an administrator attestation based on an external signed agreement; software does not independently verify resale rights.
- If provider usage is missing or exceeds the authorized reservation, funds remain held for reconciliation. Admin settlement/release requires external evidence and administrator attestation.
- Safepay refund processing is based on signed webhook events and mock tests; no merchant sandbox/live transaction has been executed.
- A refund can create a negative credit balance when credits have already been spent. This is an internal credit reversal, not a bank-account debit or an automated refund payout to the payer.
- No production deployment, live commercial service or revenue-generation claim is made.
- Keep PR #1 Draft/Open until latest CI, review, security and operational gates are complete.
