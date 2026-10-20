"""22 - Conditional writes: create-only, update-only-if-exists, and business-rule guards."""

from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p22-conditional-writes")


def attempt(label, fn):
    try:
        fn()
        show(label, "OK")
    except ClientError as e:
        show(label, e.response["Error"]["Code"])


item = {"PK": "USER#alice", "SK": "PROFILE", "name": "Alice", "credits": 10, "status": "active"}

# 1. Create-only: never overwrite an existing item.
create = lambda: table.put_item(Item=item, ConditionExpression="attribute_not_exists(PK)")
attempt("Create alice (first time)", create)
attempt("Create alice again (would overwrite)", create)

# 2. Update-only-if-exists: UpdateItem otherwise upserts a new item.
attempt(
    "Update bob (doesn't exist)",
    lambda: table.update_item(
        Key={"PK": "USER#bob", "SK": "PROFILE"},
        UpdateExpression="SET #n = :n",
        ConditionExpression="attribute_exists(PK)",
        ExpressionAttributeNames={"#n": "name"},
        ExpressionAttributeValues={":n": "Bob"},
    ),
)

# 3. Business rule: spend credits only if there are enough and the account is active.
spend = lambda amount: table.update_item(
    Key={"PK": "USER#alice", "SK": "PROFILE"},
    UpdateExpression="SET credits = credits - :a",
    ConditionExpression="credits >= :a AND #s = :active",
    ExpressionAttributeNames={"#s": "status"},
    ExpressionAttributeValues={":a": amount, ":active": "active"},
)
attempt("Spend 7 credits", lambda: spend(7))
attempt("Spend 7 more (only 3 left)", lambda: spend(7))

# 4. See *why* it failed: ask for the item as it was when the condition failed.
try:
    table.meta.client.update_item(
        TableName=table.name,
        Key={"PK": "USER#alice", "SK": "PROFILE"},
        UpdateExpression="SET credits = credits - :a",
        ConditionExpression="credits >= :a",
        ExpressionAttributeValues={":a": 7},
        ReturnValuesOnConditionCheckFailure="ALL_OLD",
    )
except ClientError as e:
    # Error responses aren't auto-deserialized, so convert the raw {"S": ...} attribute values.
    raw = e.response.get("Item", {})
    show("Item at failure time", {k: TypeDeserializer().deserialize(v) for k, v in raw.items()})

show("Final state", table.get_item(Key={"PK": "USER#alice", "SK": "PROFILE"})["Item"])
