# 25 · Transactions

**Run:** `just run 25`

## Problem

Placing an order touches three items. You create the order, decrement stock and bump the customer's order count. If one write succeeds and another fails, the data is inconsistent: an order without stock taken, or stock taken without an order.

## Pattern

Use `TransactWriteItems` for all-or-nothing writes. Each action can have its own `ConditionExpression`. If any condition fails, nothing is written.

| Action | Key                          | Condition                  |
|--------|------------------------------|----------------------------|
| Put    | `USER#alice` / `ORDER#o1`    | `attribute_not_exists(PK)` |
| Update | `PRODUCT#widget` / `STOCK`   | `stock >= :qty`            |
| Update | `USER#alice` / `PROFILE`     | none                       |

- When a transaction fails, the error includes `CancellationReasons`, one per action, so you can see which condition failed.
- `ClientRequestToken` makes the call idempotent for 10 minutes. A retry with the same token does not apply the writes twice.
- `TransactGetItems` reads up to 100 items as one consistent snapshot.

## Why

- **Correctness.** Use it for invariants that span items: stock never goes negative, a username stays unique (see [26](../26-unique-constraints/26-unique-constraints.md)), a balance transfer debits and credits together.
- **No custom saga or rollback code** for the simple cases.

## Trade-offs

- **Twice the cost.** Each item in a transaction uses 2 WCUs/RCUs instead of 1.
- **Limits.** Up to 100 actions and 4 MB total. You can't touch the same item twice in one transaction.
- **Conflicts.** Concurrent transactions on the same items fail with `TransactionConflict`. Hot items in transactions make contention worse.
- You can't read a value and then use it in the same transaction. Conditions only compare against constants you pass in.
- For a single-item invariant, a conditional write is cheaper ([22](../22-conditional-writes/22-conditional-writes.md)), and so is an atomic counter ([24](../24-atomic-counters/24-atomic-counters.md)).

## Gotchas

- `TransactionCanceledException` is a `ClientError`. Read `e.response["CancellationReasons"]`; the error message alone is vague.
- Transactions work within one region. On global tables, other regions see the writes replicated item by item, not as one atomic unit ([40](../../08-operations/40-global-tables/40-global-tables.md)).
- Streams emit one record per item, not one per transaction ([31](../../06-lifecycle-and-events/31-streams-cdc/31-streams-cdc.md)).
