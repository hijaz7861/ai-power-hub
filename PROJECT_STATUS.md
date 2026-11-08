# AI POWER HUB — PROJECT STATUS

Last updated: 2026-11-08

## Current milestone: Commercial supplier registry and pricing controls

### Implemented in feat/backend-foundation
- [x] FastAPI application, root, health, and provisional readiness endpoints
- [x] SQLAlchemy users, credit accounts, and credit ledger entries
- [x] Registration, login, authenticated profile, and short-lived bearer tokens
- [x] Scrypt password hashing
- [x] Credit debit domain primitive with idempotency and overdraw protection
- [x] Provider configuration catalogue with explicit non-operational status
- [x] HTTPS-only async OpenAI-compatible adapter with bounded timeout and sanitised failures
- [x] Mock-transport tests for provider request/response handling; no live supplier call claimed
- [x] Integer-safe wholesale-to-retail pricing engine using minor currency units and basis points
- [x] Supplier wholesale-offer persistence and Alembic migration
- [x] Customer/admin role field and admin-only API authorization
- [x] Explicit CLI-only bootstrap that promotes an existing registered account; no public role-promotion endpoint
- [x] Admin-only supplier offer create/list endpoints
- [x] Contract gate prevents an offer being activated unless an administrator marks its commercial contract verified
- [x] Admin-only retail-price preview calculated from supplier wholesale cost and configurable cost/margin inputs
- [x] Next.js + TypeScript dashboard and CI workflows
- [x] Commercial architecture and project documentation

### Latest verified CI
- [x] Backend CI #131: 30 tests passed; Alembic upgrade validation passed
- [x] Frontend CI #28: TypeScript type check and production build passed
- [ ] Termux-native install and runtime confirmed
- [ ] PostgreSQL integration tests and backup/restore drill
- [ ] Live provider call, supplier permission and invoice reconciliation

### Remaining milestones
- [ ] PostgreSQL deployment configuration, integration tests and backup/restore validation
- [ ] Rate limiting, abuse controls and request-size/time limits
- [ ] Admin management UI, audit events and admin account lifecycle controls
- [ ] Credit purchase/grant workflow with auditable settlement
- [ ] Payment provider selection and verified payment webhook lifecycle
- [ ] Subscription plans, renewals, cancellation and failed-payment state machine
- [ ] Live supplier credentials, model allowlists, live calls and supplier invoice/cost reconciliation
- [ ] Persisted retail price policies and customer-visible service catalogue
- [ ] Metered AI orchestration, usage recording, reserve/capture/refund and idempotent settlement
- [ ] Frontend authentication, protected dashboard and chat UI
- [ ] Image/audio/video provider integrations
- [ ] Contributor node agent, opt-in consent, sandbox, quotas, proof of work and payout settlement
- [ ] Security review, privacy/retention review and end-to-end tests
- [ ] Production deployment, monitoring, incident response and restore validation

## Operational and commercial limitations

- A provider is not operational until a real API call, usage accounting and supplier-cost reconciliation are verified.
- A configured API key is not evidence of resale rights. Commercial distribution permission must be confirmed separately.
- contract_status=verified is an administrator assertion based on an external agreement; the application does not independently validate legal documents.
- Supplier offer management and quote preview are admin-only. There is no public customer quote or unmetered AI execution endpoint.
- The CLI bootstrap only promotes an existing account and requires BOOTSTRAP_ADMIN_ENABLED=true plus BOOTSTRAP_ADMIN_EMAIL; disable the flag after use.
- A payment is not verified by an uploaded screenshot alone.
- Credit balances must never be increased through an unauthenticated public endpoint.
- Production schema changes must use reviewed migrations; production startup must not create tables automatically.
- Passing CI does not establish production readiness. No production-readiness or revenue-generation claim is made.
