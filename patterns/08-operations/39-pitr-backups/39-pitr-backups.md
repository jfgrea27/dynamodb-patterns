# 39 · Point-in-time recovery & backups

**Run:** `just run 39`

## Problem

A bad deploy, a buggy migration or a fat-fingered script overwrites or deletes data. DynamoDB replicates for durability, but it faithfully replicates your mistakes too. You need a way back.

## Pattern

Use both kinds of backup:

| Feature                       | What it is                                         | Use for                                  |
|-------------------------------|----------------------------------------------------|------------------------------------------|
| **Point-in-time recovery (PITR)** | continuous backup; restore to any second in the last 1–35 days | accidental writes/deletes, bad deploys   |
| **On-demand backup**          | named full snapshot, kept until deleted            | before migrations, compliance, long retention |
| **AWS Backup**                | schedules, retention rules, cross-account/region copies | org-wide backup policy                   |

```python
client.update_continuous_backups(
    TableName="orders",
    PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True, "RecoveryPeriodInDays": 35},
)
client.create_backup(TableName="orders", BackupName="before-migration")
client.restore_table_to_point_in_time(
    SourceTableName="orders", TargetTableName="orders-restored",
    RestoreDateTime=datetime(2026, 10, 20, 9, 55),
)
```

**DynamoDB Local doesn't implement any backup APIs.** The script makes the real calls, prints "unknown operation", and then uses a scan-and-write-back snapshot as a stand-in.

## Why

- **PITR is the cheapest insurance you can buy.** Turn it on for every table that matters, ideally by default in your IaC.
- Backups have **no performance impact** and use no table capacity.

## Trade-offs

- **A restore always creates a new table.** You then either point the app at it, or copy the damaged items back. A partial copy-back is usually better, because writes made after the incident are kept.
- Restores take minutes to hours, depending on table size.
- The restored table does **not** keep everything: auto scaling policies, TTL settings, IAM policies, CloudWatch alarms, tags and stream settings must be set again. GSIs and LSIs can be included.
- PITR is billed per GB-month of table size.

## Gotchas

- Deleting a table with PITR keeps a system backup for 35 days. Enable **deletion protection** (`DeletionProtectionEnabled=True`) as well.
- TTL deletes are also "real" deletes. PITR can bring back expired items if you restore to an earlier time ([30](../../06-lifecycle-and-events/30-ttl-expiry/30-ttl-expiry.md)).
- For long-term archival or analytics, use Export to S3 instead ([41](../41-analytics-export/41-analytics-export.md)). It also needs PITR enabled.
