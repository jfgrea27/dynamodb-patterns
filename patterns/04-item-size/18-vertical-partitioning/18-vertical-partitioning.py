"""18 - Vertical partitioning: split one big logical entity into several items under the same PK."""

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import client, recreate_table, show

table = recreate_table("p18-vertical-partitioning")

# One "product" as a single fat item: every read pays for the description, reviews, etc.
fat = {
    "PK": "PRODUCT#p1", "SK": "ALL",
    "name": "Kettle", "price": 30, "stock": 12,
    "description": "x" * 20_000,
    "specs": {f"spec{i}": "y" * 100 for i in range(100)},
    "reviews": [{"user": f"u{i}", "text": "z" * 200} for i in range(100)],
}
table.put_item(Item=fat)
resp = table.get_item(Key={"PK": "PRODUCT#p1", "SK": "ALL"}, ReturnConsumedCapacity="TOTAL")
show("Fat item: read units to show name + price", resp["ConsumedCapacity"]["CapacityUnits"])

# Split by access pattern: hot/small fields vs. cold/large fields, same PK.
with table.batch_writer() as batch:
    batch.put_item(Item={"PK": "PRODUCT#p2", "SK": "SUMMARY", "name": "Kettle", "price": 30})
    batch.put_item(Item={"PK": "PRODUCT#p2", "SK": "INVENTORY", "stock": 12})  # changes often
    batch.put_item(Item={"PK": "PRODUCT#p2", "SK": "DETAILS", "description": fat["description"], "specs": fat["specs"]})
    for r in fat["reviews"]:
        batch.put_item(Item={"PK": "PRODUCT#p2", "SK": f"REVIEW#{r['user']}", **r})

# Listing page: only the summary.
resp = table.get_item(Key={"PK": "PRODUCT#p2", "SK": "SUMMARY"}, ReturnConsumedCapacity="TOTAL")
show("Split: read units for SUMMARY", resp["ConsumedCapacity"]["CapacityUnits"])

# Stock updates now write a tiny item instead of rewriting the whole product.
resp = table.update_item(
    Key={"PK": "PRODUCT#p2", "SK": "INVENTORY"},
    UpdateExpression="ADD stock :d",
    ExpressionAttributeValues={":d": -1},
    ReturnConsumedCapacity="TOTAL",
)
show("Split: write units for a stock change", resp["ConsumedCapacity"]["CapacityUnits"])
resp = table.update_item(
    Key={"PK": "PRODUCT#p1", "SK": "ALL"},
    UpdateExpression="ADD stock :d",
    ExpressionAttributeValues={":d": -1},
    ReturnConsumedCapacity="TOTAL",
)
show("Fat item: write units for the same stock change", resp["ConsumedCapacity"]["CapacityUnits"])

# Product page: the whole item collection in ONE query (sorted by SK, so name SKs deliberately).
resp = table.query(KeyConditionExpression=Key("PK").eq("PRODUCT#p2"), Limit=5)
show("Item collection query (first 5 by SK)", [i["SK"] for i in resp["Items"]])

# Or fetch exactly the parts you need with BatchGetItem.
resp = client.batch_get_item(RequestItems={table.name: {"Keys": [
    {"PK": "PRODUCT#p2", "SK": "SUMMARY"},
    {"PK": "PRODUCT#p2", "SK": "INVENTORY"},
]}})
show("Summary + inventory via BatchGetItem", sorted(i["SK"] for i in resp["Responses"][table.name]))
