# AI POWER HUB — PROJECT STATUS

Last updated: 2026-11-08

## Current milestone: Customer account foundation and audited credit operations

### Implemented in feat/backend-foundation
- [x] FastAPI application, root, health, and provisional readiness endpoints
- [x] SQLAlchemy users, credit accounts, supplier offers, and credit ledger
- [x] Alembic migrations through 0003_credit_grant_actor
- [x] Registration, login, authenticated profile, and short-lived bearer tokens
- [x] Scrypt password hashing
- [x] Customer/admin role field and admin-only API authorization
- [x] Explicit CLI-only bootstrap that promotes an existing registered account
- [x] Credit debit domain primitive with strict integer validation, idempotency, and overdraw protection
- [x] Admin-only manual credit grants with reason, idempotency and actor-linked ledger audit
- [x] Authenticated, paginated customer credit ledger restricted to the current user
- [x] Provider configuration catalogue with explicit non-operational status
- [x] HTTPS-only async OpenAI-compatible adapter with bounded timeout and sanitised failures
- [x] Mock-transport provider adapter tests; no live supplier call claimed
- [x] Integer-safe wholesale-to-retail pricing engine using minor currency units and basis points
- [x] Admin-only supplier offer create/list and retail-price preview endpoints
- [x] Commercial contract activation gate for supplier offers
- [x] Next.js dashboard with registration/login/logout server routes
- [x] HttpOnly, SameSite=Strict session cookie; token is not stored in browser localStorage
- [x] Account panel showing user identity, credit balance and recent ledger activity
- [x] Commercial architecture, admin bootstrap, supplier registry and project documentation

### Latest verified GitHub Actions
- [x] Backend CI #180: 39 tests passed; Alembic upgrades 0001 -> 0002 -> 0003 passed
- [x] Frontend CI #56: TypeScript type check and Next.js production build passed
- [ ] Browser-based end-to-end login/register/logout test
- [ ] Termux-native install and runtime confirmed

### Remaining engineering milestones
- [ ] PostgreSQL deployment configuration, integration tests and backup/restore validation
- [ ] Rate limiting, abuse controls, request-size limits and CSRF/origin protection for future state-changing cookie-authenticated routes
- [ ] Admin management UI, audit-event search and admin account lifecycle controls
- [ ] Customer-facing chat UI and conversation persistence
- [ ] Metered AI orchestration, usage recording, reserve/capture/refund and idempotent settlement
- [ ] Live supplier credentials, model allowlists, live calls, supplier invoice/cost reconciliation and resale permissions
- [ ] Persisted retail price policies and customer-visible service catalogue
- [ ] Payment gateway selection, verified webhook lifecycle, credit purchase settlement and subscriptions
- [ ] Image/audio/video integrations
- [ ] Contributor node agent, opt-in consent, sandbox, quotas, proof of work and payout settlement
- [ ] Security review, privacy/retention review and end-to-end tests
- [ ] Production deployment, monitoring, incident response and restore validation

## Operational and commercial limitations

- Provider adapter is mock-tested only. No live API call, supplier account, negotiated wholesale rate or reseller agreement has been verified.
- A configured API key is not evidence of resale rights.
- contract_status=verified is an administrator assertion based on an external agreement; the application does not independently validate legal documents.
- Admin credit grant is a manual support/promotional adjustment, not proof of payment and not a customer purchase endpoint.
- There is no public unmetered AI execution endpoint.
- The CLI bootstrap only promotes an existing account and requires BOOTSTRAP_ADMIN_ENABLED=true plus BOOTSTRAP_ADMIN_EMAIL; disable the flag after use.
- Credit balances must never be increased through an unauthenticated public endpoint.
- Production schema changes must use reviewed migrations; production startup must not create tables automatically.
- Passing CI does not establish production readiness. No production-readiness or revenue-generation claim is made.
