# 27 · Idempotency keys

**Run:** `just run 27`

## Problem

Networks fail after the work is done but before the response arrives. Clients, SDKs, queues (SQS, EventBridge) and Lambda all retry. Without protection, a retried "charge card" request charges twice.

## Pattern

The client sends a unique **idempotency key** with each logical request. The server records it in DynamoDB.

| PK                     | SK       | status                     | response     | expiresAt   |
|------------------------|----------|----------------------------|--------------|-------------|
| `IDEMPOTENCY#req-123`  | `RECORD` | `IN_PROGRESS`/`COMPLETED`  | stored result| epoch + 24h |

1. **Claim:** `PutItem` with `attribute_not_exists(PK)`. Only the first request wins.
2. **Work:** do the side effect once.
3. **Complete:** store the response and set `status = COMPLETED`.
4. **Retry:** the conditional put fails. Read the record and return the stored response. If it is still `IN_PROGRESS`, tell the client to retry later.

A TTL on `expiresAt` cleans up old records ([30](../../06-lifecycle-and-events/30-ttl-expiry/30-ttl-expiry.md)).

## Why

- Gives you **exactly-once effects** on top of at-least-once delivery.
- Retries become safe everywhere: API handlers, SQS consumers, stream processors.

## Trade-offs

- An extra write (or two) per request.
- **Crashes.** If you crash between claim and complete, the record stays `IN_PROGRESS`. Give it a short in-progress timeout so it can be reclaimed, e.g. an `inProgressExpiry` attribute in the claim condition.
- The side effect itself (e.g. a payment provider) should also accept your idempotency key. DynamoDB can't roll back an external call.

## Gotchas

- Derive the key from the client's request ID or a hash of the payload, not from a server-side timestamp.
- Decide what a retry with the same key but a *different* payload means. Usually it's an error: store a payload hash and compare.
- AWS Lambda Powertools (`aws_lambda_powertools.utilities.idempotency`) implements this pattern on top of DynamoDB.
- Related: conditional writes ([22](../22-conditional-writes/22-conditional-writes.md)), transactions with `ClientRequestToken` ([25](../25-transactions/25-transactions.md)).
