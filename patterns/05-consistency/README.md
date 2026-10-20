# 05 · Consistency & concurrency

How to stay correct when many clients write at once. DynamoDB has no locks in the usual sense. Instead every write can carry a **condition** that is checked atomically, and every pattern in this section is built from that one primitive (plus transactions for multi-item cases).

## Key ideas

- **Conditional writes** reject a write unless the item is in an expected state: it doesn't exist yet, a field has a given value, there's enough balance left.
- **Optimistic locking** is a conditional write on a `version` number. Read, change, write only if the version hasn't moved, and retry if it has.
- **Atomic updates** (`ADD`, `SET x = x + :n`) change a value server-side, with no read-modify-write race.
- **Transactions** make up to 100 writes all-or-nothing. They're also how you enforce uniqueness on a non-key attribute (write a sentinel item in the same transaction).
- **Idempotency keys** make retries safe: record the request ID with a condition, so the second attempt returns the stored result.
- **GSIs lag behind the table.** Never use a GSI read to decide whether a write is safe.
- **Distributed locks** are conditional writes with a lease, for the rare cases that genuinely need mutual exclusion.

## Lessons

| # | Lesson | You'll learn |
|---|---|---|
| 22 | [Conditional writes](22-conditional-writes/22-conditional-writes.md) | Create-only, update-if-exists, business-rule conditions |
| 23 | [Optimistic locking](23-optimistic-locking/23-optimistic-locking.md) | Version checks and a retry loop |
| 24 | [Atomic counters](24-atomic-counters/24-atomic-counters.md) | `ADD` vs read-then-write under concurrency; floors and sequences |
| 25 | [Transactions](25-transactions/25-transactions.md) | `TransactWriteItems`, cancellation reasons, `TransactGetItems` |
| 26 | [Unique constraints](26-unique-constraints/26-unique-constraints.md) | Sentinel items for unique emails; changing a unique value |
| 27 | [Idempotency keys](27-idempotency-keys/27-idempotency-keys.md) | Exactly-once effects for retried requests |
| 28 | [GSIs are eventually consistent](28-gsi-eventual-consistency/28-gsi-eventual-consistency.md) | Why GSI reads can be stale, and the workarounds |
| 29 | [Distributed locking](29-distributed-locking/29-distributed-locking.md) | Leases, heartbeats, owner-checked release, takeover |

**Before:** [04-item-size](../04-item-size/README.md) · **Next:** [06-lifecycle-and-events](../06-lifecycle-and-events/README.md)
