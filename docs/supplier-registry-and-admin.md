# Supplier registry and administrator bootstrap

## Purpose

The supplier registry records wholesale offers and gives administrators a controlled
retail-price preview. It is not a supplier marketplace contract system and does not
prove that an offer is commercially resellable.

## Administrator bootstrap

1. Register the intended administrator through the ordinary registration endpoint.
2. Back up the database and ensure the account email is correct.
3. Run the command from the repository root with the production database URL set:

   BOOTSTRAP_ADMIN_ENABLED=true
   BOOTSTRAP_ADMIN_EMAIL=admin@example.com
   python -m backend.scripts.bootstrap_admin

4. Immediately remove BOOTSTRAP_ADMIN_ENABLED from the environment after use.
5. Log in again and verify that administrator-only endpoints are accessible.

The command only promotes an existing account. There is no public API for role
promotion. Protect the database and runtime environment; anyone with database
write access can still change roles.

## Supplier offers

Administrator endpoints:

- GET /api/v1/admin/supplier-offers
- POST /api/v1/admin/supplier-offers
- POST /api/v1/admin/supplier-offers/{offer_id}/quote

Allowed service classes: ai_api, gpu_compute, cloud, storage, web_data.

Allowed billing units include per-1k input/output tokens, per request, per GPU
second, per GB-month and per-1k results. Monetary amounts are integer minor units:
PKR uses paisa and USD uses cents. The current registry accepts PKR and USD.

Offers default to contract_status=pending and is_active=false. The API rejects
activation unless an administrator sets the contract status to verified.
That value is an administrative assertion based on an independently reviewed
commercial agreement; the platform does not validate a contract or confer resale
rights. Keep a copy of the agreement in the organization's controlled records.

## Retail-price preview

The quote endpoint uses the offer's wholesale amount as supplier cost and accepts
additional contributor, infrastructure and support costs, target margin, payment
fee and tax rates. It returns a preview only; it does not publish a customer price,
charge credits, call a supplier, or settle an invoice.

Do not activate or sell an offer until the supplier identity, model/service,
jurisdiction, commercial permission, unit of measure, currency, taxes, actual
usage metering and invoice reconciliation are confirmed.

## Verification

Backend CI exercises role denial, admin supplier-offer creation/listing, contract
activation gating, retail-price preview, provider adapter mocks and migrations.
Live supplier credentials and commercial contracts are external prerequisites.
