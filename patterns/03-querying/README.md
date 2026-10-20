# 03 · Querying

How to read data efficiently once the keys are designed. DynamoDB charges for what it **reads**, not what it **returns**. The lessons here are about making those two numbers the same, and about handling the API's paging and batching behaviour correctly.

## Key ideas

- **Query, don't Scan.** `Query` reads one partition. `Scan` reads the whole table. Parallel Scan is for batch jobs only.
- **Filters don't save money.** A `FilterExpression` runs after the read. Put selectivity into the key instead.
- **Everything is paged.** Responses stop at 1 MB, or at `Limit`. Follow `LastEvaluatedKey`, and expose it to API clients as an opaque cursor.
- **Choose index projections deliberately.** `KEYS_ONLY`, `INCLUDE` or `ALL` trades index storage and write cost against follow-up reads.
- **Batch calls can partially fail.** `BatchWriteItem` and `BatchGetItem` return unprocessed items, which you must retry with backoff.

## Lessons

| # | Lesson | You'll learn |
|---|---|---|
| 12 | [Avoid Scan (parallel Scan for batch jobs)](12-avoid-scan-parallel-scan/12-avoid-scan-parallel-scan.md) | The cost difference between Scan and Query; segmented parallel scans |
| 13 | [Filter expressions don't reduce cost](13-filter-expressions-cost/13-filter-expressions-cost.md) | Measuring read units for filters vs key conditions; the `Limit` + filter trap |
| 14 | [Pagination with cursors](14-pagination-cursors/14-pagination-cursors.md) | `LastEvaluatedKey`, opaque API cursors, boto3 paginators |
| 15 | [GSI projections](15-gsi-projections/15-gsi-projections.md) | What each projection type returns and costs |
| 16 | [Batch operations with retries](16-batch-retries/16-batch-retries.md) | Chunking to 25/100, retrying unprocessed items, `batch_writer()` |

**Before:** [02-modelling](../02-modelling/README.md) · **Next:** [04-item-size](../04-item-size/README.md)
