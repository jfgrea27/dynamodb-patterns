"""12 - Avoid Scan in hot paths; use parallel Scan for batch jobs."""

from concurrent.futures import ThreadPoolExecutor

from boto3.dynamodb.conditions import Attr, Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p12-avoid-scan")

with table.batch_writer() as batch:
    for u in range(200):
        for o in range(5):
            batch.put_item(Item={"PK": f"USER#{u}", "SK": f"ORDER#{o}", "total": o * 10})

# Bad: find one user's orders by scanning the whole table.
resp = table.scan(FilterExpression=Attr("PK").eq("USER#42"), ReturnConsumedCapacity="TOTAL")
show(
    "Scan + filter for USER#42",
    {"returned": resp["Count"], "examined": resp["ScannedCount"], "consumed": resp.get("ConsumedCapacity")},
)

# Good: Query reads only that partition.
resp = table.query(KeyConditionExpression=Key("PK").eq("USER#42"), ReturnConsumedCapacity="TOTAL")
show(
    "Query for USER#42",
    {"returned": resp["Count"], "examined": resp["ScannedCount"], "consumed": resp.get("ConsumedCapacity")},
)

# Batch job (export, migration, backfill): parallel scan split into segments.
TOTAL_SEGMENTS = 4


def scan_segment(segment):
    count, kwargs = 0, {"Segment": segment, "TotalSegments": TOTAL_SEGMENTS}
    while True:
        page = table.scan(**kwargs)
        count += page["Count"]
        if "LastEvaluatedKey" not in page:
            return count
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


with ThreadPoolExecutor(max_workers=TOTAL_SEGMENTS) as pool:
    per_segment = list(pool.map(scan_segment, range(TOTAL_SEGMENTS)))
show("Parallel scan: items per segment", {"segments": per_segment, "total": sum(per_segment)})
