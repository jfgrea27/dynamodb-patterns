"""11 - Denormalization: copy data onto the items that read it; pay on writes, save on reads."""

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import client, recreate_table, show

table = recreate_table("p11-denormalization")

# Option A: duplicate small, rarely-changing fields onto child items.
# Each order carries the customer's name, so "list orders" needs no second lookup.
with table.batch_writer() as batch:
    batch.put_item(Item={"PK": "CUST#c1", "SK": "PROFILE", "name": "Carol", "tier": "gold"})
    for oid in ["o1", "o2", "o3"]:
        batch.put_item(Item={"PK": "CUST#c1", "SK": f"ORDER#{oid}", "customerName": "Carol", "total": 10})

resp = table.query(KeyConditionExpression=Key("PK").eq("CUST#c1") & Key("SK").begins_with("ORDER#"))
show("Orders with customer name (1 query, no join)", [(i["SK"], i["customerName"]) for i in resp["Items"]])

# Option B: embed a bounded list as a map/list attribute (one-to-few).
table.put_item(Item={
    "PK": "CUST#c1", "SK": "ADDRESSES",
    "addresses": {"home": {"city": "London"}, "work": {"city": "Leeds"}},
})
show("Embedded addresses", table.get_item(Key={"PK": "CUST#c1", "SK": "ADDRESSES"})["Item"]["addresses"])

# The cost: when the source changes, every copy must change too.
# Here we fan out in one transaction (max 100 items) so the copies never disagree.
new_name = "Carol Smith"
order_keys = [{"PK": i["PK"], "SK": i["SK"]} for i in resp["Items"]]
client.transact_write_items(TransactItems=[
    {"Update": {
        "TableName": table.name,
        "Key": {"PK": "CUST#c1", "SK": "PROFILE"},
        "UpdateExpression": "SET #n = :n",
        "ExpressionAttributeNames": {"#n": "name"},
        "ExpressionAttributeValues": {":n": new_name},
    }},
    *[{"Update": {
        "TableName": table.name,
        "Key": k,
        "UpdateExpression": "SET customerName = :n",
        "ExpressionAttributeValues": {":n": new_name},
    }} for k in order_keys],
])
resp = table.query(KeyConditionExpression=Key("PK").eq("CUST#c1"))
show("After rename, all copies updated", [(i["SK"], i.get("name") or i.get("customerName")) for i in resp["Items"]])
