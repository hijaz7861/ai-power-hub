# AI POWER HUB — PROJECT STATUS

Last updated: 2026-11-08

## Current milestone: Safepay sandbox top-up and verified credit settlement foundation

### Implemented in feat/backend-foundation
- [x] FastAPI application, health/readiness endpoints and SQLAlchemy persistence
- [x] Alembic migrations through 0005_payment_orders
- [x] Registration/login, scrypt password hashing, short-lived bearer tokens and customer/admin roles
- [x] CLI-only bootstrap for an existing administrator account
- [x] Idempotent credit debit, admin manual grant with actor audit, and current-user-scoped ledger history
- [x] Integer-safe wholesale-to-retail pricing engine and admin supplier offer registry
- [x] HTTPS-only OpenAI-compatible adapter with mock tests; no live AI supplier call claimed
- [x] Next.js registration/login/logout using HttpOnly SameSite=Strict session cookie
- [x] Customer account panel, credit balance, recent ledger activity and top-up form
- [x] Safepay Express Checkout adapter using server-side API/secret keys and fixed sandbox/production hosts
- [x] PKR top-up orders with 100 PKR minimum, 100,000 PKR maximum and per-user idempotency
- [x] 1 credit = 1 paisa; a successful PKR 100 top-up grants 10,000 credits
- [x] Checkout return/cancel pages and owner-scoped payment status API
- [x] Raw-body HMAC-SHA512 webhook verification, merchant identity check and event replay/collision protection
- [x] Payment settlement only after exact order reference/tracker, amount, currency and TRACKER_ENDED state match
- [x] Duplicate success events cannot grant credits twice; amount mismatches are recorded without crediting
- [x] Refund events are flagged for manual review; no automatic credit reversal is performed
- [x] Admin-only payment event inbox and minimal event metadata storage
- [x] Documentation for provider setup, supplier agreements, admin bootstrap and payment lifecycle

### Latest verified GitHub Actions
- [x] Backend CI #266: 55 tests passed; Alembic migrations 0001 through 0005 passed
- [x] Frontend CI #100: TypeScript type check and Next.js production build passed
- [ ] Real Safepay sandbox transaction and signed webhook delivery
- [ ] Browser-based end-to-end test of register, login, checkout return and balance refresh
- [ ] Termux-native install and runtime confirmed

### Remaining engineering milestones
- [ ] Safepay sandbox merchant account, API key, secret key, webhook secret and public HTTPS callback configuration
- [ ] Verify payment outcome against Safepay reporter API and periodic provider reconciliation
- [ ] Refund, partial refund, chargeback and dispute state machine with safe credit reversal policy
- [ ] Payment receipts and admin reconciliation dashboard
- [ ] Persisted retail price policies, service catalogue and metered AI request orchestration
- [ ] Credit reserve/capture/refund for actual AI usage, with provider token usage and cost reconciliation
- [ ] Live AI supplier credentials, model allowlists, live calls and resale permissions
- [ ] PostgreSQL integration, backup/restore validation and production database rollout
- [ ] Rate limiting, abuse controls, CSRF/origin protection and request-size/time limits
- [ ] Admin management UI and audit-event search
- [ ] Customer chat UI and conversation persistence
- [ ] Subscription plans, renewals and cancellation state machine
- [ ] Image/audio/video integrations
- [ ] Opt-in contributor node agent, sandbox, quotas, proof-of-work verification and contributor payouts
- [ ] Security/privacy review, end-to-end tests, production deployment and monitoring

## Payment and commercial limitations

- The Safepay integration is implemented and mock-tested only. No merchant credentials or live sandbox payment have been supplied or used.
- Configure SAFEPAY_API_KEY, SAFEPAY_SECRET_KEY, SAFEPAY_WEBHOOK_SECRET, SAFEPAY_ENVIRONMENT=sandbox and PUBLIC_APP_URL on the backend only.
- Configure the provider webhook URL as PUBLIC_APP_URL + /api/v1/webhooks/safepay. Use sandbox credentials and sandbox webhook secret first.
- A successful browser redirect is not proof of payment. Only the signed, matching payment.succeeded event with TRACKER_ENDED and exact amount/currency can grant credits.
- A payment refund event is recorded for review; credits are not automatically reversed until a dispute/refund policy is implemented.
- Supplier contract_status=verified remains an administrator assertion based on an external signed agreement.
- Provider adapters and CI passing do not establish live commercial rights or production readiness.
- No production-readiness or revenue-generation claim is made.
