# 13 · Filter expressions don't reduce cost

**Run:** `just run 13`

## Problem

`FilterExpression` looks like a SQL `WHERE`, but it runs **after** the read. You pay for every item the key condition matched, even the ones the filter throws away. In the script, "open orders" via a filter reads 1,000 items (~127 RCUs) to return 10.

## Pattern

Put the selectivity in the **key**, so the key condition only touches the items you want.

| PK            | SK                              |
|---------------|---------------------------------|
| `CUSTOMER#c1` | `ORDER#0000`                    |
| `CUSTOMER#c1` | `STATUS#OPEN#ORDER#0000`        |
| `CUSTOMER#c1` | `STATUS#SHIPPED#ORDER#0001`     |

`Query(PK=CUSTOMER#c1, SK begins_with STATUS#OPEN#)` reads 10 items (~1.5 RCUs).

Other ways to do the same:

- Composite sort keys ([05](../../02-modelling/05-composite-sort-keys/05-composite-sort-keys.md)).
- A GSI keyed on the attribute ([09](../../02-modelling/09-gsi-overloading/09-gsi-overloading.md)).
- A sparse index that only holds matching items ([10](../../02-modelling/10-sparse-index/10-sparse-index.md)).

## Why

- Cost and latency follow the items **read**, not the items returned.

## Trade-offs

- Extra keys or GSIs cost writes and storage, and must be kept in sync when the status changes.
- Filters are **fine** when they drop only a small share of what you read, e.g. hiding soft-deleted or TTL-expired items ([30](../../06-lifecycle-and-events/30-ttl-expiry/30-ttl-expiry.md), [33](../../06-lifecycle-and-events/33-soft-delete-archival/33-soft-delete-archival.md)).

## Gotchas

- **`Limit` applies before the filter.** A page can come back with 0 items and still have a `LastEvaluatedKey`. Keep paging until it's gone ([14](../14-pagination-cursors/14-pagination-cursors.md)).
- The 1 MB page size is also measured before the filter.
- `ScannedCount` vs `Count` in the response tells you how much a filter wasted. Log it.
