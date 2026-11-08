# AI POWER HUB — PROJECT STATUS

Last updated: 2026-11-08

## Current milestone: Customer accounts, supplier registry and payment webhook foundation

### Implemented in feat/backend-foundation
- [x] FastAPI application, health/readiness endpoints and SQLAlchemy persistence
- [x] Alembic migrations through 0004_payment_webhook_inbox
- [x] Registration, login, authenticated profile and scrypt password hashing
- [x] Short-lived bearer tokens and customer/admin role authorization
- [x] CLI-only admin bootstrap for an existing registered account
- [x] Idempotent credit debit with strict integer validation and overdraw protection
- [x] Admin-only manual credit grant with reason, idempotency and actor-linked audit record
- [x] Authenticated customer credit history restricted to current user
- [x] Admin-only supplier wholesale-offer registry and retail-price preview
- [x] Supplier offer activation gate requiring admin assertion of verified commercial contract
- [x] Integer-safe wholesale-to-retail pricing engine
- [x] HTTPS-only async OpenAI-compatible adapter with mocked transport tests; no live AI provider call claimed
- [x] Next.js dashboard with registration/login/logout server routes and HttpOnly SameSite=Strict session cookie
- [x] Account panel showing identity, balance and recent credit activity
- [x] Safepay webhook inbox with raw-body HMAC-SHA512 signature verification
- [x] Webhook replay protection using unique event token and payload hash collision detection
- [x] Minimal webhook metadata persistence; customer email and raw webhook body are not stored
- [x] Admin-only payment event inbox view
- [x] Documentation for supplier registry, admin bootstrap, credit ledger and Safepay webhook setup

### Latest verified GitHub Actions before webhook inbox additions
- [x] Backend CI #180: 39 tests passed; Alembic migrations 0001 through 0003 passed
- [x] Frontend CI #56: TypeScript type check and production build passed
- [ ] Fresh Backend CI for migration 0004 and webhook tests
- [ ] Fresh Frontend CI for latest head
- [ ] Browser-based end-to-end authentication test
- [ ] Termux-native install and runtime confirmed

### Remaining engineering milestones
- [ ] Safepay sandbox payment-order/checkout creation and tracker reconciliation
- [ ] Payment order state machine, webhook-to-order matching and verified credit settlement
- [ ] Payment refunds, chargebacks, reconciliation and customer receipts
- [ ] Payment gateway merchant sandbox account and webhook endpoint configuration
- [ ] Persisted retail price policies and customer-visible service catalogue
- [ ] Metered AI orchestration, usage recording, reserve/capture/refund and idempotent settlement
- [ ] Live AI supplier credentials, model allowlists, calls, supplier invoices and resale permissions
- [ ] PostgreSQL integration, backup/restore validation and production database rollout
- [ ] Rate limiting, abuse controls, CSRF/origin protection and request-size/time limits
- [ ] Admin management UI and audit-event search
- [ ] Customer chat UI and conversation persistence
- [ ] Subscription plans and renewal/cancellation state machine
- [ ] Image/audio/video integrations
- [ ] Opt-in contributor node agent, sandbox, quotas, proof-of-work verification and payouts
- [ ] Security/privacy review, end-to-end tests and production monitoring
- [ ] Production deployment and incident response

## Payment and commercial limitations

- Safepay webhook receiver is a signed event inbox only. It does not create checkout sessions, link events to payment orders, mark orders paid, or credit users.
- Webhook secret must be configured server-side as SAFEPAY_WEBHOOK_SECRET. Sandbox and production secrets are distinct.
- A verified webhook event is not sufficient by itself to grant credits until a pending payment order, exact amount, currency, tracker and customer are reconciled.
- Safepay sandbox access is available through its developer onboarding; production requires separate merchant onboarding.
- No live payment or live AI provider transaction has been performed.
- Supplier contract_status=verified remains an administrator assertion based on an external agreement.
- Admin credit grant is a manual support/promotional adjustment, not proof of payment.
- No production-readiness or revenue-generation claim is made.
