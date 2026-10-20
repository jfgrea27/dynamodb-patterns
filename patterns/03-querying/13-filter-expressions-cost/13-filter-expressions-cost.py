"""13 - Filter expressions don't reduce cost: put selectivity in the key."""

from boto3.dynamodb.conditions import Attr, Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p13-filter-cost")

# 1 000 orders for one customer, only 10 of them OPEN. ~1 KB each.
padding = "x" * 1000
with table.batch_writer() as batch:
    for i in range(1000):
        status = "OPEN" if i % 100 == 0 else "SHIPPED"
        batch.put_item(Item={"PK": "CUSTOMER#c1", "SK": f"ORDER#{i:04d}", "status": status, "pad": padding})
        # Second copy keyed by status - selectivity lives in the sort key.
        batch.put_item(Item={"PK": "CUSTOMER#c1", "SK": f"STATUS#{status}#ORDER#{i:04d}", "pad": padding})


def query_all(**kwargs):
    count = scanned = 0
    capacity = 0.0
    while True:
        page = table.query(ReturnConsumedCapacity="TOTAL", **kwargs)
        count += page["Count"]
        scanned += page["ScannedCount"]
        capacity += page.get("ConsumedCapacity", {}).get("CapacityUnits", 0)
        if "LastEvaluatedKey" not in page:
            return {"returned": count, "read": scanned, "RCUs": capacity}
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


show(
    "FilterExpression status=OPEN (reads everything, then discards)",
    query_all(
        KeyConditionExpression=Key("PK").eq("CUSTOMER#c1") & Key("SK").begins_with("ORDER#"),
        FilterExpression=Attr("status").eq("OPEN"),
    ),
)
show(
    "KeyCondition SK begins_with STATUS#OPEN# (reads only matches)",
    query_all(KeyConditionExpression=Key("PK").eq("CUSTOMER#c1") & Key("SK").begins_with("STATUS#OPEN#")),
)

# Limit applies BEFORE the filter: you can get 0 results and still have more pages.
page = table.query(
    KeyConditionExpression=Key("PK").eq("CUSTOMER#c1") & Key("SK").begins_with("ORDER#"),
    FilterExpression=Attr("status").eq("OPEN"),
    Limit=50,
    ExclusiveStartKey={"PK": "CUSTOMER#c1", "SK": "ORDER#0001"},
)
show("Limit=50 + filter", {"returned": page["Count"], "read": page["ScannedCount"], "more": "LastEvaluatedKey" in page})
