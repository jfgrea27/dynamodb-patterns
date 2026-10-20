# 41 · Analytics outside DynamoDB

**Run:** `just run 41`

## Problem

"Revenue by country last quarter." "Top 100 customers." Questions like these need to read the **whole table** and group or sort by attributes that aren't keys. In DynamoDB that means a full Scan: slow, expensive, and it eats the capacity your live traffic needs ([12](../../03-querying/12-avoid-scan-parallel-scan/12-avoid-scan-parallel-scan.md)).

## Pattern

**DynamoDB serves the application. Analytics runs on a copy.**

| Option                              | How                                                      | Freshness        |
|-------------------------------------|----------------------------------------------------------|------------------|
| **Export to S3** + Athena / Glue / Spark | `ExportTableToPointInTime`, full or incremental, in DynamoDB JSON or Ion | snapshot (minutes–hours) |
| **Zero-ETL to Redshift / OpenSearch** | managed integration, no pipeline code                   | near real-time   |
| **Streams → Firehose → S3**         | change events into a data lake ([31](../../06-lifecycle-and-events/31-streams-cdc/31-streams-cdc.md)) | near real-time   |

```python
client.export_table_to_point_in_time(
    TableArn=table_arn,
    S3Bucket="my-analytics-bucket",
    S3Prefix="exports/orders",
    ExportFormat="DYNAMODB_JSON",        # or "ION"
    ExportType="INCREMENTAL_EXPORT",     # or "FULL_EXPORT" (default)
)
```

Then in Athena:

```sql
SELECT item.country.S AS country, COUNT(*) AS orders, SUM(CAST(item.total.N AS int)) AS revenue
FROM orders_export GROUP BY 1;
```

DynamoDB Local has no export API. The script instead does a 4-segment parallel scan into gzipped files in the same `{"Item": {...}}` line format a real export writes, then runs the GROUP BY in Python.

## Why

- **Exports use no table capacity.** They read from PITR backups, not the live table.
- **The right tool.** SQL engines do joins, GROUP BY and ad-hoc filters; DynamoDB doesn't.
- **Cheap.** S3 storage and per-query Athena pricing beat scanning the table again and again.

## Trade-offs

- **Data is a little stale.** A snapshot, or seconds to minutes behind with zero-ETL or streams.
- Another system to manage: a Glue catalog, partitions, and schema drift from DynamoDB's schemaless items.
- Single-table designs ([04](../../02-modelling/04-single-table-design/04-single-table-design.md)) export as one mixed table. You'll need views per entity type (`WHERE item.type.S = 'Order'`).

## Gotchas

- Export needs **PITR enabled** on the table ([39](../39-pitr-backups/39-pitr-backups.md)).
- Numbers are exported as strings (`{"N": "42"}`). Cast them in SQL.
- If you *must* scan the live table (small table, one-off job), use a parallel scan from a client (boto3 clients are thread-safe, resource objects aren't), consider a rate limiter, and prefer eventually consistent reads.
