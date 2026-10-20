# 08 · Operations

Running DynamoDB in production: choosing a capacity mode, protecting data, going multi-region and getting data out for analytics without hurting the live table.

## Key ideas

- **Capacity modes.** On-demand needs no planning and scales instantly. Provisioned with auto-scaling is cheaper for steady, predictable traffic. You can switch between them.
- **Backups.** Point-in-time recovery restores to any second in the last 35 days. On-demand backups are kept until you delete them. Restores always create a *new* table.
- **Global tables** replicate a table across regions, active-active. Concurrent writes to the same item resolve as last-writer-wins, so route each item's writes to one home region when that matters.
- **Analytics belongs elsewhere.** Export to S3 (it uses no table capacity) and query with Athena, or use zero-ETL to Redshift or OpenSearch. Don't run reporting Scans against the live table.

## Lessons

| # | Lesson | You'll learn |
|---|---|---|
| 38 | [Capacity modes](38-capacity-modes/38-capacity-modes.md) | Sizing read/write units; switching modes; auto-scaling |
| 39 | [PITR & backups](39-pitr-backups/39-pitr-backups.md) | Enabling PITR, on-demand backups, restore-to-new-table |
| 40 | [Global tables](40-global-tables/40-global-tables.md) | Adding replicas; last-writer-wins and how to avoid losing writes |
| 41 | [Analytics outside DynamoDB](41-analytics-export/41-analytics-export.md) | Export to S3 format; querying the export instead of the table |

DynamoDB Local doesn't support most of these APIs, so the demos show the real calls and simulate the behaviour.

**Before:** [07-performance-and-scale](../07-performance-and-scale/README.md) · **Next:** [09-anti-patterns](../09-anti-patterns/README.md)
