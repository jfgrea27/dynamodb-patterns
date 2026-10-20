"""02 - Access-pattern-first design: list the queries, then derive keys from them."""

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import gsi, recreate_table, show

# Step 1: write the access patterns down BEFORE choosing keys.
ACCESS_PATTERNS = [
    ("Get customer by id", "GetItem  PK=CUST#<id>, SK=PROFILE"),
    ("List a customer's orders, newest first", "Query    PK=CUST#<id>, SK begins_with ORDER#"),
    ("Get an order by id", "Query    GSI1 GSI1PK=ORDER#<id>"),
    ("List orders by status for a day", "Query    GSI2 GSI2PK=STATUS#<status>, GSI2SK begins_with <date>"),
]
show("Access patterns -> key design", [f"{name:<42} {how}" for name, how in ACCESS_PATTERNS])

# Step 2: the table + indexes fall straight out of that list.
table = recreate_table("p02-access-patterns", gsis=[gsi("GSI1"), gsi("GSI2")])


def order(cust, order_id, date, status, total):
    return {
        "PK": f"CUST#{cust}",
        "SK": f"ORDER#{date}#{order_id}",
        "GSI1PK": f"ORDER#{order_id}",  # lookup by order id
        "GSI1SK": f"ORDER#{order_id}",
        "GSI2PK": f"STATUS#{status}",  # orders by status + date
        "GSI2SK": f"{date}#{order_id}",
        "type": "Order",
        "orderId": order_id,
        "status": status,
        "total": total,
    }


with table.batch_writer() as batch:
    batch.put_item(Item={"PK": "CUST#c1", "SK": "PROFILE", "type": "Customer", "name": "Carol"})
    batch.put_item(Item=order("c1", "o1", "2026-10-19", "SHIPPED", 30))
    batch.put_item(Item=order("c1", "o2", "2026-10-20", "PENDING", 12))
    batch.put_item(Item=order("c2", "o3", "2026-10-20", "PENDING", 55))

# Step 3: verify every access pattern is a single key-based request (no Scan).
show("AP1 customer", table.get_item(Key={"PK": "CUST#c1", "SK": "PROFILE"})["Item"])

resp = table.query(
    KeyConditionExpression=Key("PK").eq("CUST#c1") & Key("SK").begins_with("ORDER#"),
    ScanIndexForward=False,
)
show("AP2 customer orders", [i["orderId"] for i in resp["Items"]])

resp = table.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq("ORDER#o3"))
show("AP3 order by id", resp["Items"][0]["orderId"])

resp = table.query(
    IndexName="GSI2",
    KeyConditionExpression=Key("GSI2PK").eq("STATUS#PENDING") & Key("GSI2SK").begins_with("2026-10-20"),
)
show("AP4 pending orders today", [i["orderId"] for i in resp["Items"]])
