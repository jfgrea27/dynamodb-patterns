"""10 - Sparse index: only items that HAVE the GSI key attribute appear in the index."""

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import gsi, recreate_table, show

table = recreate_table("p10-sparse-index", gsis=[gsi("OpenOrders", pk="openOrdersPK", sk="openSince")])

# 1000 orders, only a handful still open. Only open orders get the index attributes.
with table.batch_writer() as batch:
    for n in range(1000):
        item = {"PK": f"ORDER#{n:04}", "SK": "ORDER", "status": "CLOSED"}
        if n % 200 == 0:
            item |= {"status": "OPEN", "openOrdersPK": "OPEN", "openSince": f"2026-10-{n // 100 + 1:02}"}
        batch.put_item(Item=item)

resp = table.query(IndexName="OpenOrders", KeyConditionExpression=Key("openOrdersPK").eq("OPEN"))
show("Open orders (read from the index only)", [i["PK"] for i in resp["Items"]])
show("Items examined", {"index_query": resp["ScannedCount"], "table_size": 1000})

# Closing an order: REMOVE the attributes and it drops out of the index.
table.update_item(
    Key={"PK": "ORDER#0000", "SK": "ORDER"},
    UpdateExpression="SET #s = :closed REMOVE openOrdersPK, openSince",
    ExpressionAttributeNames={"#s": "status"},
    ExpressionAttributeValues={":closed": "CLOSED"},
)
resp = table.query(IndexName="OpenOrders", KeyConditionExpression=Key("openOrdersPK").eq("OPEN"))
show("After closing ORDER#0000", [i["PK"] for i in resp["Items"]])
