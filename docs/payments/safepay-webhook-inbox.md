# Safepay Express Checkout and credit settlement

## Provider flow

Safepay's Express Checkout documentation describes this server-side sequence:
create a payment session/tracker, request a short-lived time-based token (TBT),
build a hosted checkout URL, then receive the shopper's return and payment event.
The implementation follows that documented sequence and uses fixed provider hosts.

Official references:
- Express Checkout: https://apidocs.getsafepay.com/
- Safepay developer guide: https://safepay.pk/docs/developers
- Webhook overview: https://safepay-docs.netlify.app/developers/webhooks/overview/
- Webhook event types: https://safepay-docs.netlify.app/developers/webhooks/webhook-types/
- HMAC verification: https://safepay-docs.netlify.app/developers/webhooks/verify-hmac-signatures/

## Customer top-up

Authenticated endpoints:

- POST /api/v1/payments/topups
- GET /api/v1/payments/topups/{reference}

The top-up request accepts PKR 100 through PKR 100,000 and a per-user idempotency
key. The server creates a pending payment order, requests a Safepay payment
session and short-lived TBT, and returns a hosted checkout URL. The API key and
secret key never leave the backend. The customer can only retrieve their own
payment order.

The product accounting convention is 1 credit = 1 paisa. Thus a PKR 100
successful top-up grants 10,000 credits. Amounts are sent to Safepay in the
currency's lowest denomination.

The browser is redirected to the hosted checkout. Return/cancel URLs include the
internal order reference. A return redirect never changes the payment status or
grants credits by itself.

## Webhook verification and settlement

Public endpoint:

- POST /api/v1/webhooks/safepay

The receiver:
1. Requires SAFEPAY_WEBHOOK_SECRET and SAFEPAY_API_KEY configured server-side.
2. Reads raw body with a 1 MiB limit.
3. Verifies X-SFPY-SIGNATURE using HMAC-SHA512 over the exact raw body.
4. Confirms the event merchant_api_key equals the configured merchant API key.
5. Deduplicates event token and rejects token reuse with a different payload.
6. Resolves an order by provider tracker first, then by metadata order
   reference as a fallback. A successful payment still requires a matching
   provider tracker; if an order reference is supplied, it must match exactly.
7. Requires payment.succeeded, TRACKER_ENDED, exact expected amount and exact
   currency before crediting the account.
8. Locks the matched payment-order row during settlement and refund processing,
   then writes the account balance, ledger entry and order state in one database
   transaction. PostgreSQL row locking serializes distinct webhook events for
   the same order; duplicate event tokens are independently idempotent.

Only minimal event metadata and a SHA-256 body digest are stored. Raw webhook
payloads and customer email addresses are not persisted. Amount/currency/order
mismatches are recorded without issuing credits.

Failed payment events are recorded as failed attempts; they do not grant credits
or prematurely mark an order terminal. Refund events require both the exact
provider tracker and internal order reference, a paid order, matching currency,
a positive refund amount and a provider refund state consistent with the
cumulative refunded total. Verified partial/full refunds reverse purchased
credits and write an idempotent refund ledger entry. If the customer has already
spent those credits, the balance can become negative and further paid usage
remains blocked until replenished. Invalid or inconsistent refund events are
retained for manual review; this is an internal credit reversal, not a bank/card
refund payout. Chargebacks and dispute workflows are not automated.

## Backend environment

Set these values on the backend only:

- SAFEPAY_API_KEY
- SAFEPAY_SECRET_KEY
- SAFEPAY_WEBHOOK_SECRET
- SAFEPAY_ENVIRONMENT=sandbox
- PUBLIC_APP_URL=https://your-public-domain

Configure the Safepay webhook target as:
PUBLIC_APP_URL + /api/v1/webhooks/safepay

Use the sandbox dashboard credentials and sandbox webhook secret first. Do not
commit keys, put them in frontend variables, or paste them into chat. The public
application URL must be HTTPS.

## Not yet verified

- No Safepay merchant account or credentials were supplied.
- No live sandbox checkout or signed webhook delivery has been performed.
- The provider reporter API is not yet polled for reconciliation.
- Refunds, partial refunds, disputes and chargebacks are not automated.
- Production onboarding, legal terms, MDR/fees, tax and settlement bank account
  must be confirmed with Safepay before launch.

The code and mocked tests establish an integration foundation, not a live payment
gateway or production-ready payment operation.
