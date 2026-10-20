# 11 · Denormalization and duplication

**Run:** `just run 11`

## Problem

A screen lists a customer's orders with the customer's name. Normalized, that's one query for orders plus a lookup for the customer. Across many screens, those extra reads add up in latency and cost.

## Pattern

Copy data to where it is read. Two common forms:

**A. Duplicate fields onto child items.** Good for small fields that rarely change.

| PK        | SK          | name / customerName | total |
|-----------|-------------|---------------------|-------|
| `CUST#c1` | `PROFILE`   | Carol               |       |
| `CUST#c1` | `ORDER#o1`  | Carol               | 10    |
| `CUST#c1` | `ORDER#o2`  | Carol               | 10    |

**B. Embed a bounded collection** as a map or list on one item, e.g. a customer's few addresses. This works for "one-to-few" relationships.

When the source changes, update every copy. Do it in a transaction ([25](../../05-consistency/25-transactions/25-transactions.md)) if the copies must agree, or asynchronously from a stream ([31](../../06-lifecycle-and-events/31-streams-cdc/31-streams-cdc.md)) if a short lag is fine.

## Why

- Reads take one request and are cheap. Most apps read far more than they write.
- It fits DynamoDB's model: pre-compute the join at write time.

## Trade-offs

- More work on writes, and a risk of copies drifting apart.
- Bigger items mean more read and write units.

## Rules of thumb

- Duplicate **immutable** or **rarely-changing** data freely (names, created dates, product titles at order time).
- Don't duplicate fast-changing data (stock levels, counters). Reference it instead.
- Embed only when the collection is **bounded** and small. Unbounded lists hit the 400 KB limit ([17](../../04-item-size/17-small-items-item-collections/17-small-items-item-collections.md)).

## Gotchas

- Sometimes the copy is the right answer for history. The price *at order time* shouldn't change when the catalog changes.
- A transaction can touch at most 100 items. Large fan-outs need streams or batches.

Related: [04](../04-single-table-design/04-single-table-design.md), [18](../../04-item-size/18-vertical-partitioning/18-vertical-partitioning.md).
