# 22 · Conditional writes

**Run:** `just run 22`

## Problem

`PutItem` replaces whatever is there, and `UpdateItem` creates the item if it doesn't exist (an upsert). Without guards you get accidental overwrites, "ghost" items made by updates, and broken business rules (negative balances, double bookings).

## Pattern

Add a `ConditionExpression` to the write. DynamoDB checks it **atomically on the server** and rejects the write with `ConditionalCheckFailedException` if it's false.

| Goal                         | Condition                                       |
|------------------------------|-------------------------------------------------|
| Create only, no overwrite    | `attribute_not_exists(PK)`                      |
| Update only if item exists   | `attribute_exists(PK)`                          |
| Optimistic lock              | `version = :expected` ([23](../23-optimistic-locking/23-optimistic-locking.md)) |
| Business rule                | `credits >= :amount AND #status = :active`      |
| State machine transition     | `#status = :from` (e.g. only PENDING → PAID)    |

## Why

- Atomic check-and-write with no transaction and no lock.
- Costs the same as a normal write.
- The building block for uniqueness ([26](../26-unique-constraints/26-unique-constraints.md)), idempotency ([27](../27-idempotency-keys/27-idempotency-keys.md)) and locks ([29](../29-distributed-locking/29-distributed-locking.md)).

## Trade-offs

- A condition can only look at the **one item** being written. For rules across several items use [25-transactions](../25-transactions/25-transactions.md) (`ConditionCheck`).
- A failed write still uses write capacity.

## Gotchas

- `attribute_not_exists(PK)` means "no item with this full key exists". It does not check the whole partition.
- Reserved words (`status`, `name`, `count`…) need `ExpressionAttributeNames` (`#s`).
- Pass `ReturnValuesOnConditionCheckFailure="ALL_OLD"` to get the current item back on failure. This saves a re-read. The item comes back in raw `{"S": ...}` form, so deserialize it (see the script).
