# 32 · Streams-maintained aggregates

**Run:** `just run 32`

## Problem

"How many orders does this store have, and what's the revenue?" DynamoDB has no `COUNT(*)` or `SUM()`. Computing it at read time means querying every order item, which gets slower and more expensive as data grows.

## Pattern

Store the answer as its own item, and keep it current from the **stream** ([31](../31-streams-cdc/31-streams-cdc.md)). Writers only write orders. A stream consumer turns each change into a delta and applies it with an atomic `ADD` ([24](../../05-consistency/24-atomic-counters/24-atomic-counters.md)).

| PK         | SK          | type  | attributes             |
|------------|-------------|-------|------------------------|
| `STORE#s1` | `ORDER#o1`  | Order | total=42               |
| `STORE#s1` | `ORDER#o2`  | Order | total=20               |
| `STORE#s1` | `STATS`     | —     | orderCount=2, revenue=62 |

Delta rules (with `NEW_AND_OLD_IMAGES`):

- `INSERT` → count +1, revenue +new
- `MODIFY` → count 0, revenue +(new − old)
- `REMOVE` → count −1, revenue −old

Reads become a single `GetItem(PK=STORE#s1, SK=STATS)`.

## Why

- **Cheap reads.** O(1) instead of O(number of orders).
- **Writers stay simple.** No extra update or transaction on the hot path.
- **No contention on the write path.** Many writers don't fight over the stats item, because only the consumer updates it.

## Trade-offs

- **Eventually consistent.** The aggregate lags the orders by the stream delay (usually under a second).
- **At-least-once delivery.** A retried batch can apply a delta twice. For exact numbers, record processed `eventID`s or the stream sequence number and skip duplicates ([27](../../05-consistency/27-idempotency-keys/27-idempotency-keys.md)). Or rebuild periodically from the source.
- A very hot aggregate item can still hit the 1,000 WCU per partition limit. Batch deltas in the consumer (sum a whole batch, then one `ADD`) or shard the counter ([35](../../07-performance-and-scale/35-write-sharding/35-write-sharding.md)).
- The alternative is updating the aggregate inside a `TransactWriteItems` with the order ([25](../../05-consistency/25-transactions/25-transactions.md)). That is strongly consistent, but costs 2x and serializes writers on one item.

## Gotchas

- The consumer's own writes to the `STATS` item also appear on the stream. Filter them out (the script checks `type == "Order"`). Otherwise you get an infinite loop. In AWS, use event-source-mapping **filter criteria** to drop them before the Lambda runs.
