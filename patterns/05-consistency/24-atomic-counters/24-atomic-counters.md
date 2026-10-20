# 24 · Atomic counters

**Run:** `just run 24`

## Problem

Page views, likes, stock levels and sequence numbers all need increments. Reading the value, adding one in code and writing it back loses updates when two clients do it at once. The script shows 50 "increments" ending at a much smaller number.

## Pattern

Let DynamoDB do the arithmetic with `UpdateItem`:

```python
table.update_item(
    Key={"PK": "POST#hello-world", "SK": "STATS"},
    UpdateExpression="ADD #v :one",
    ExpressionAttributeNames={"#v": "views"},
    ExpressionAttributeValues={":one": 1},
    ReturnValues="UPDATED_NEW",  # optional: get the new value back
)
```

- `ADD` (or `SET x = if_not_exists(x, :zero) + :one`) is applied atomically on the server.
- Add a `ConditionExpression` for a **bounded counter**, e.g. `remaining > :zero` so tickets never oversell.
- `ReturnValues="UPDATED_NEW"` turns a counter into a **sequence generator** (invoice numbers).

## Why

- **No lost updates.** No read is needed, so there is no race.
- **One round trip.** No optimistic-lock retry loop ([23](../23-optimistic-locking/23-optimistic-locking.md)).

## Trade-offs

- **Not idempotent.** If the request times out and you retry it, you may count twice. That's fine for view counts but not for money. Use idempotency keys ([27](../27-idempotency-keys/27-idempotency-keys.md)) or a transaction with a `ClientRequestToken` ([25](../25-transactions/25-transactions.md)) when exact counts matter.
- **Hot keys.** A single counter item is limited to about 1,000 WCU/s. For very high write rates, shard the counter ([35](../../07-performance-and-scale/35-write-sharding/35-write-sharding.md)) or aggregate from a stream ([32](../../06-lifecycle-and-events/32-streams-aggregates/32-streams-aggregates.md)).

## Gotchas

- Many common names are reserved words (`views`, `count`, `name`, `status`, `total`, `next`...). Use `ExpressionAttributeNames`.
- `ADD` on a missing attribute starts at 0. `SET x = x + :n` fails on a missing attribute unless you wrap it in `if_not_exists`.
- Numbers come back as `Decimal` in boto3.
