# 10 · Sparse index

**Run:** `just run 10`

## Problem

You want "all open orders" or "all VIP users". These are a small subset of a large table. A `Scan` with a filter reads (and bills) every item ([13](../../03-querying/13-filter-expressions-cost/13-filter-expressions-cost.md)).

## Pattern

A GSI only contains items that **have its key attributes**. Set those attributes only on the items you want in the subset:

| PK           | status | openOrdersPK | openSince    | In index? |
|--------------|--------|--------------|--------------|-----------|
| `ORDER#0000` | OPEN   | `OPEN`       | `2026-10-01` | yes       |
| `ORDER#0001` | CLOSED | –            | –            | no        |
| `ORDER#0200` | OPEN   | `OPEN`       | `2026-10-03` | yes       |

- **Read the subset:** `Query OpenOrders openOrdersPK=OPEN`
- **Leave the subset:** `UpdateItem ... REMOVE openOrdersPK, openSince`

## Why

- The query reads only the matching items, so cost tracks the subset, not the table.
- The index is small, so storage and write costs are low. Only items in the index cost GSI writes.

## Trade-offs

- The app must add and remove the attributes at the right moments. Bugs here leave stale entries.
- A constant partition key (`OPEN`) puts the whole subset in one partition. That's fine while it's small; shard it if it gets big or busy ([35](../../07-performance-and-scale/35-write-sharding/35-write-sharding.md)).

## Gotchas

- GSI key attributes must be String, Number or Binary. Booleans can't be keys, so use `"Y"` or a timestamp.
- Use `REMOVE` to leave the index. Setting the attribute to an empty string is an error.

Related: [09](../09-gsi-overloading/09-gsi-overloading.md), [33](../../06-lifecycle-and-events/33-soft-delete-archival/33-soft-delete-archival.md).
