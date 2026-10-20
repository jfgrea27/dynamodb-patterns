"""15 - Choose GSI projections deliberately: KEYS_ONLY vs INCLUDE vs ALL."""

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import client, gsi, recreate_table, show

table = recreate_table(
    "p15-gsi-projections",
    gsis=[
        gsi("ByStatusKeys", pk="status", sk="createdAt", projection="KEYS_ONLY"),
        gsi("ByStatusInclude", pk="status", sk="createdAt", projection="INCLUDE", include=["customer", "total"]),
        gsi("ByStatusAll", pk="status", sk="createdAt", projection="ALL"),
    ],
)

with table.batch_writer() as batch:
    for i in range(5):
        batch.put_item(
            Item={
                "PK": f"ORDER#{i}",
                "SK": "ORDER",
                "status": "OPEN",
                "createdAt": f"2026-10-0{i + 1}",
                "customer": f"cust-{i}",
                "total": 10 * i,
                "lineItems": "big blob of line items " * 50,  # large, rarely needed on list views
            }
        )

for index in ["ByStatusKeys", "ByStatusInclude", "ByStatusAll"]:
    item = table.query(IndexName=index, KeyConditionExpression=Key("status").eq("OPEN"), Limit=1)["Items"][0]
    show(f"{index}: attributes returned", sorted(item))

# KEYS_ONLY needs a second round trip to get the rest of the item.
keys = table.query(IndexName="ByStatusKeys", KeyConditionExpression=Key("status").eq("OPEN"))["Items"]
full = client.batch_get_item(
    RequestItems={
        table.name: {
            "Keys": [{"PK": k["PK"], "SK": k["SK"]} for k in keys],
            "ProjectionExpression": "PK, customer, #t",
            "ExpressionAttributeNames": {"#t": "total"},
        }
    }
)
show("KEYS_ONLY + BatchGetItem (2nd request)", len(full["Responses"][table.name]))

# Index storage: ALL copies every attribute (and every write to them).
desc = client.describe_table(TableName=table.name)["Table"]["GlobalSecondaryIndexes"]
show("Index sizes (Local reports the same number for each; on AWS ALL > INCLUDE > KEYS_ONLY)", {d["IndexName"]: d.get("IndexSizeBytes") for d in desc})
