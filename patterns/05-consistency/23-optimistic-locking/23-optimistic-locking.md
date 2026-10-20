# 23 · Optimistic locking

**Run:** `just run 23`

## Problem

Two clients read the same item, change it in memory, and write it back. The second write silently overwrites the first: a **lost update**. DynamoDB has no row locks.

## Pattern

Keep a `version` number on the item. Every write says "only if the version is still what I read" and increments it:

```python
table.put_item(
    Item={**item, "version": v + 1},
    ConditionExpression="version = :v",
    ExpressionAttributeValues={":v": v},
)
```

If someone else wrote in between, the call fails with `ConditionalCheckFailedException`. The client then re-reads, re-applies its change and retries.

| PK           | SK     | balance | version |
|--------------|--------|---------|---------|
| `ACCOUNT#a1` | `META` | 150     | 2       |

## Why

- No locks to hold, expire or clean up. Contention is detected at write time.
- Costs no more than a normal write (a failed condition still uses write capacity).
- Works with `PutItem`, `UpdateItem`, `DeleteItem` and transactions.

## Trade-offs

- Under heavy contention, clients retry a lot. Use a pessimistic lock ([29-distributed-locking](../29-distributed-locking/29-distributed-locking.md)) or restructure the data.
- For simple numeric changes, an atomic `ADD` ([24-atomic-counters](../24-atomic-counters/24-atomic-counters.md)) or a guarded `UpdateItem` (`SET balance = balance - :x` with `balance >= :x`) avoids the read entirely.

## Gotchas

- Re-read with `ConsistentRead=True` before retrying. Otherwise you may get the stale version again.
- Cap the retries and add jitter.
- The Java SDK's DynamoDBMapper `@DynamoDBVersionAttribute` and PynamoDB's `VersionAttribute` do this for you.
- Related: [22-conditional-writes](../22-conditional-writes/22-conditional-writes.md).
