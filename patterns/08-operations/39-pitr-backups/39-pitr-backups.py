"""39 - Point-in-time recovery & backups: turn PITR on, take on-demand backups, restore to a new table."""

from botocore.exceptions import ClientError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import client, recreate_table, show

TABLE = "p39-pitr-backups"
table = recreate_table(TABLE)
table.put_item(Item={"PK": "ACCOUNT#1", "SK": "META", "balance": 100})


def attempt(label, fn, **kwargs):
    """Run an AWS call; DynamoDB Local doesn't implement most backup APIs, so report what happened."""
    try:
        resp = fn(**kwargs)
        resp.pop("ResponseMetadata", None)
        show(f"{label}: OK", resp)
        return resp
    except ClientError as e:
        show(f"{label}: not supported by DynamoDB Local", e.response["Error"].get("Message") or e.response["Error"]["Code"])
    except Exception as e:  # e.g. unknown operation
        show(f"{label}: failed", f"{type(e).__name__}: {e}")


# 1. Point-in-time recovery: continuous backups, restore to any second in the last 1-35 days.
attempt(
    "Enable PITR",
    client.update_continuous_backups,
    TableName=TABLE,
    PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True, "RecoveryPeriodInDays": 35},
)
attempt("Describe continuous backups", client.describe_continuous_backups, TableName=TABLE)

# 2. On-demand backup: a named snapshot kept until you delete it (e.g. before a risky migration).
backup = attempt("Create on-demand backup", client.create_backup, TableName=TABLE, BackupName="before-migration")

# Local stand-in for a backup: a full scan we can write back later.
local_snapshot = table.scan()["Items"]

# 3. Oops - a bad deploy zeroes the balance.
table.update_item(Key={"PK": "ACCOUNT#1", "SK": "META"}, UpdateExpression="SET balance = :z", ExpressionAttributeValues={":z": 0})
show("After bad deploy", table.get_item(Key={"PK": "ACCOUNT#1", "SK": "META"})["Item"])

# 4. Restore. Restores ALWAYS create a NEW table; you then swap traffic or copy items back.
attempt(
    "Restore to latest restorable time",
    client.restore_table_to_point_in_time,
    SourceTableName=TABLE,
    TargetTableName=f"{TABLE}-restored",
    UseLatestRestorableTime=True,
)
if backup:
    attempt(
        "Restore from backup",
        client.restore_table_from_backup,
        TargetTableName=f"{TABLE}-from-backup",
        BackupArn=backup["BackupDetails"]["BackupArn"],
    )

# Local fallback: write the snapshot back (in AWS you'd copy from the restored table, or swap to it).
with table.batch_writer() as w:
    for item in local_snapshot:
        w.put_item(Item=item)
show("Local stand-in: restored from snapshot", table.get_item(Key={"PK": "ACCOUNT#1", "SK": "META"})["Item"])
