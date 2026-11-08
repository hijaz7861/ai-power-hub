# Safepay webhook inbox

## Provider choice and prerequisites

Safepay is the first Pakistan-focused payment integration candidate because its
developer documentation describes PKR payment flows, a free sandbox environment
and a separate production onboarding process. The platform does not claim a
merchant account exists.

Official references:
- API reference: https://apidocs.getsafepay.com/
- Developer setup: https://safepay.pk/docs/developers
- Webhook overview: https://safepay-docs.netlify.app/developers/webhooks/overview/
- Webhook event types: https://safepay-docs.netlify.app/developers/webhooks/webhook-types/
- HMAC verification: https://safepay-docs.netlify.app/developers/webhooks/verify-hmac-signatures/

## Current implementation

Public endpoint:

- POST /api/v1/webhooks/safepay

The endpoint:
1. Requires SAFEPAY_WEBHOOK_SECRET configured server-side.
2. Reads the raw request body with a 1 MiB size limit.
3. Verifies the X-SFPY-SIGNATURE header using HMAC-SHA512 over the exact raw bytes.
4. Parses the JSON only after signature verification.
5. Validates the event token/type and minimal tracker, amount and currency fields.
6. Stores only the event token, event type, tracker token, amount, currency, SHA-256 payload digest and processing status.
7. Deduplicates repeated event tokens and rejects token reuse with a different payload.

Raw webhook bodies and customer email addresses are not persisted. The admin-only
GET /api/v1/admin/payment-events endpoint exposes the minimal inbox metadata.

## Important non-functionality

This is not yet a payment integration or payment confirmation workflow. It does
not create Safepay trackers/checkout sessions, link a webhook to a pending payment
order, query the provider, grant credits, process refunds or reconcile settlement.
A successful redirect or webhook alone must not grant credits without matching
the provider tracker, user, expected amount and currency against a pending order.

Sandbox and production webhook secrets are different. Never put the secret in
frontend variables, source code, GitHub files or logs. Do not configure production
webhooks until a merchant account and public HTTPS endpoint exist.

## Verification

Backend tests cover valid HMAC, invalid signatures, missing configuration,
malformed JSON, invalid amounts, event deduplication and event-token collision.
No live Safepay request or payment has been performed.
