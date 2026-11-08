# AI Power Network — commercial architecture

## Product decision

AI Power Hub is the customer-facing platform and AI Power Network is its supply,
routing and settlement layer. The business is an infrastructure aggregator:
procure authorised AI/API, GPU, cloud, storage and data services at negotiated
wholesale rates; add verified contributor capacity where technically and
contractually permitted; then sell metered services at independently configured
retail prices.

The platform must not represent a supplier as integrated until a real account,
commercial permission, live request, usage measurement and invoice/cost
reconciliation have been verified.

## Supply classes

1. **Licensed AI/API suppliers** — model inference and other vendor APIs. Obtain
   explicit reseller/white-label or other commercial rights before resale.
2. **Cloud/GPU suppliers** — burst capacity for workloads that cannot run on
   phones or edge devices.
3. **Contributor nodes** — opt-in CPU, GPU, storage or network retrieval. Each
   workload class needs a separate capability profile, sandbox, resource quota,
   privacy policy and proof of completed work.
4. **First-party AI services** — workflows and applications owned by AI Power Hub.

A mobile device is an edge node, not a general-purpose data-centre GPU. Never
turn a contributor device into an undisclosed proxy, VPN exit, or traffic relay.
No private-network scanning, credential harvesting, or arbitrary third-party
code execution is allowed.

## Commercial pricing

Use integer minor currency units (PKR paisa) and integer basis points. The
pricing engine accounts for supplier cost, contributor payout, infrastructure,
support, payment processing, tax and target contribution margin. The engine
rounds prices upward and rejects configurations where fees, tax and target
margin consume all revenue.

The quote engine is a domain primitive, not a public endpoint. Only authorised
pricing/admin services may provide supplier costs or change margin policy.
Customer-facing quotes must expose the final price and relevant taxes, never
supplier secrets or wholesale contracts.

**Unit economics:** contribution = retail revenue - supplier cost - contributor
payout - infrastructure - support - payment fees - tax. Do not scale a service
until contribution is positive under measured usage and refund/failure rates.

## Transaction lifecycle

1. Customer requests a named capability and receives a price quote.
2. Platform checks account status, credit balance, policy and capacity.
3. Customer authorises the charge or prepaid-credit reservation.
4. Scheduler selects a supplier/node using capability, jurisdiction, latency,
   reliability, price and policy constraints.
5. Adapter executes with a strict timeout, spend ceiling and request identifier.
6. Platform records supplier usage, contributor work proof and actual costs.
7. Settlement captures only the verified amount; unused reservation is released.
8. Ledger records immutable, idempotent customer, supplier and contributor entries.
9. Reconciliation compares internal usage with supplier invoices and payouts.

Retries must be idempotent. A failed or unverified job must not earn a contributor
payout. Customer credits must not be minted by a public endpoint or screenshot.

## Required bounded rollout

- **Milestone A:** pricing, provider catalogue, metering contracts and audit model.
- **Milestone B:** one authorised live provider adapter, cost accounting and
  integration tests with mocked failure/timeout/duplicate responses.
- **Milestone C:** prepaid credit purchase and admin-reviewed payment settlement.
- **Milestone D:** opt-in node agent for one safe workload class with quotas,
  signed jobs, sandboxing, health checks and verifiable completion.
- **Milestone E:** multi-supplier scheduling, contributor settlement and customer
  self-service plans.

Do not begin with a token/coin or promise passive earnings. Rewards are contractual
payouts for measured, accepted work, not speculative points.

## Launch gates

- Commercial resale rights and supplier terms reviewed.
- Data protection, consumer, tax, payment and cross-border requirements reviewed
  for each launch jurisdiction.
- API keys stored server-side in a secret manager; never sent to browsers/nodes.
- Rate limits, abuse detection, spend caps, tenant isolation and audit trails.
- PostgreSQL migrations, backup/restore drill, monitoring and incident process.
- Published service status distinguishes prototype, sandbox and production.
