# 09 · Anti-patterns

The common ways DynamoDB designs go wrong, each measured in the demo so you can see the cost, with a pointer to the pattern that fixes it. Use this as a review checklist for an existing table.

## What to look for

| Anti-pattern | Symptom | Fix |
|---|---|---|
| One table per entity, joined in the app | Several round trips per page | [04 · Single-table design](../02-modelling/04-single-table-design/04-single-table-design.md) |
| Unbounded list inside an item | Write cost grows on every append, then the write fails at 400 KB | [17 · Keep items small](../04-item-size/17-small-items-item-collections/17-small-items-item-collections.md) |
| Low-cardinality partition key | Throttling on one hot key while the rest of the table is idle | [34 · High-cardinality keys](../07-performance-and-scale/34-high-cardinality-keys/34-high-cardinality-keys.md), [35 · Write sharding](../07-performance-and-scale/35-write-sharding/35-write-sharding.md) |
| Scan + filter in a request path | Read cost proportional to table size | [12 · Avoid Scan](../03-querying/12-avoid-scan-parallel-scan/12-avoid-scan-parallel-scan.md), [10 · Sparse index](../02-modelling/10-sparse-index/10-sparse-index.md) |
| Too many GSIs | Every write costs one extra write per index | [09 · GSI overloading](../02-modelling/09-gsi-overloading/09-gsi-overloading.md) |
| Ad-hoc analytics on the live table | Reporting jobs eat capacity and throttle the app | [41 · Analytics outside DynamoDB](../08-operations/41-analytics-export/41-analytics-export.md) |

## Lessons

| # | Lesson | You'll learn |
|---|---|---|
| 42 | [Anti-patterns](42-anti-patterns/42-anti-patterns.md) | The measured cost of each anti-pattern above |

**Before:** [08-operations](../08-operations/README.md) · **Back to:** [00-intro](../00-intro/README.md)
