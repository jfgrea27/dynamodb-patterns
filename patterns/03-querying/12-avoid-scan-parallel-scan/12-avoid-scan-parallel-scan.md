# 12 · Avoid Scan (use parallel Scan for batch jobs)

**Run:** `just run 12`

## Problem

`Scan` reads **every item in the table**, then applies any filter. Cost and latency grow with table size, not with the size of the result. In the script, finding 5 orders with Scan reads 1,000 items. A Query reads 5.

## Pattern

**In request paths, use `Query` or `GetItem` only.** If an access pattern seems to need a Scan, add a key or GSI that serves it ([02](../../02-modelling/02-access-pattern-first/02-access-pattern-first.md), [09](../../02-modelling/09-gsi-overloading/09-gsi-overloading.md)).

**For batch jobs** (migrations, backfills, re-indexing, one-off exports), use a **parallel scan**:

```python
table.scan(Segment=i, TotalSegments=N)  # one worker per segment
```

Each worker scans a disjoint slice of the table and pages through it with `LastEvaluatedKey`.

## Why

- A Query costs about the same at 1 GB as at 10 TB. A Scan does not.
- A big Scan can use all your table's capacity and throttle production traffic.
- A parallel scan finishes a full-table job N times faster.

## Trade-offs

- A parallel scan uses capacity N times faster. Rate-limit it, run it off-peak, or use on-demand mode.
- For analytics or full exports, **Export to S3** costs no table capacity at all ([41](../../08-operations/41-analytics-export/41-analytics-export.md)).

## Gotchas

- Each Scan page returns at most 1 MB. Always loop on `LastEvaluatedKey` ([14](../14-pagination-cursors/14-pagination-cursors.md)).
- `FilterExpression` doesn't reduce what you pay for ([13](../13-filter-expressions-cost/13-filter-expressions-cost.md)).
- A Scan is not a point-in-time snapshot. Items written during the scan may or may not appear.
- Small, bounded tables (e.g. a config table with 50 rows) are fine to scan.
