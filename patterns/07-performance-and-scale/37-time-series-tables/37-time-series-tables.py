"""37 - Time-series: one table per period (rotate) or time-bucketed PK + TTL."""

from datetime import datetime, timedelta, timezone

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import client, dynamodb, recreate_table, show

# --- Option A: table per month. Writes go to the current table; old tables are dropped whole. ---
now = datetime(2026, 10, 20, tzinfo=timezone.utc)
months = [(now - timedelta(days=31 * i)).strftime("%Y-%m") for i in range(3)]  # current + 2 old

tables = {m: recreate_table(f"p37-metrics-{m}") for m in months}
for m, t in tables.items():
    with t.batch_writer() as batch:
        for i in range(5):
            batch.put_item(Item={"PK": "SENSOR#s1", "SK": f"{m}-01T00:0{i}:00Z", "value": i})

show("Tables before rotation", sorted(n for n in client.list_tables()["TableNames"] if n.startswith("p37-metrics-")))

# Retention = 2 months: drop the oldest table. One API call - no per-item deletes, no WCU cost.
oldest = months[-1]
client.delete_table(TableName=f"p37-metrics-{oldest}")
client.get_waiter("table_not_exists").wait(TableName=f"p37-metrics-{oldest}")
show("Tables after dropping the oldest", sorted(n for n in client.list_tables()["TableNames"] if n.startswith("p37-metrics-")))
# On AWS you'd also lower the old tables' provisioned capacity (or use on-demand) since they're read-only now.

# --- Option B: one table, time-bucketed PK, TTL removes old items. ---
table = recreate_table("p37-metrics-ttl")
try:
    client.update_time_to_live(TableName="p37-metrics-ttl", TimeToLiveSpecification={"Enabled": True, "AttributeName": "expires_at"})
except Exception as e:
    print("TTL config failed:", e)

retention = 30 * 24 * 3600
with table.batch_writer() as batch:
    for hour in range(3):
        for minute in range(0, 60, 20):
            ts = now.replace(hour=hour, minute=minute)
            batch.put_item(
                Item={
                    "PK": f"SENSOR#s1#{ts:%Y-%m-%d}",  # one partition per sensor per day
                    "SK": ts.isoformat(),
                    "value": hour * 60 + minute,
                    "expires_at": int(ts.timestamp()) + retention,
                }
            )

resp = table.query(
    KeyConditionExpression=Key("PK").eq("SENSOR#s1#2026-10-20") & Key("SK").between("2026-10-20T01:00", "2026-10-20T02:00")
)
show("Bucketed query: 01:00-02:00", [(i["SK"], int(i["value"])) for i in resp["Items"]])
show("TTL status", client.describe_time_to_live(TableName="p37-metrics-ttl")["TimeToLiveDescription"])

# Clean up demo tables
for n in client.list_tables()["TableNames"]:
    if n.startswith("p37-metrics-2"):
        dynamodb.Table(n).delete()
