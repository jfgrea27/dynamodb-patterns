"""04 - Single-table design: many entity types, one table, generic PK/SK."""

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p04-single-table")

# Users, their orders and their addresses all share PK=USER#<id>,
# so one Query returns the whole "item collection" - no joins.
items = [
    {"PK": "USER#alice", "SK": "PROFILE", "type": "User", "name": "Alice", "email": "alice@example.com"},
    {"PK": "USER#alice", "SK": "ADDRESS#home", "type": "Address", "city": "London"},
    {"PK": "USER#alice", "SK": "ORDER#2026-10-01#o1", "type": "Order", "total": 42},
    {"PK": "USER#alice", "SK": "ORDER#2026-10-15#o2", "type": "Order", "total": 17},
    {"PK": "USER#bob", "SK": "PROFILE", "type": "User", "name": "Bob", "email": "bob@example.com"},
    {"PK": "USER#bob", "SK": "ORDER#2026-09-30#o3", "type": "Order", "total": 99},
]
with table.batch_writer() as batch:
    for item in items:
        batch.put_item(Item=item)

# Access pattern 1: get a user profile (GetItem on full key)
show("Alice's profile", table.get_item(Key={"PK": "USER#alice", "SK": "PROFILE"})["Item"])

# Access pattern 2: everything about a user in one request
resp = table.query(KeyConditionExpression=Key("PK").eq("USER#alice"))
show("Alice's whole item collection (1 query)", resp["Items"])

# Access pattern 3: only a user's orders, newest first
resp = table.query(
    KeyConditionExpression=Key("PK").eq("USER#alice") & Key("SK").begins_with("ORDER#"),
    ScanIndexForward=False,
)
show("Alice's orders, newest first", resp["Items"])

# The app layer turns rows back into typed objects using the `type` attribute.
by_type = {}
for item in table.query(KeyConditionExpression=Key("PK").eq("USER#alice"))["Items"]:
    by_type.setdefault(item["type"], []).append(item)
show("Grouped by entity type", {k: len(v) for k, v in by_type.items()})
