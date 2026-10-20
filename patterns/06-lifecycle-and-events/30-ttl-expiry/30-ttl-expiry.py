"""30 - TTL: let DynamoDB delete expired items for free."""

import time

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import client, recreate_table, show

TABLE = "p30-ttl-expiry"
table = recreate_table(TABLE)

# Enable TTL on the `expiresAt` attribute (epoch SECONDS, Number type).
try:
    client.update_time_to_live(
        TableName=TABLE,
        TimeToLiveSpecification={"Enabled": True, "AttributeName": "expiresAt"},
    )
    show("TTL status", client.describe_time_to_live(TableName=TABLE)["TimeToLiveDescription"])
except ClientError as e:
    show("UpdateTimeToLive failed", e.response["Error"]["Message"])

now = int(time.time())
with table.batch_writer() as batch:
    batch.put_item(Item={"PK": "USER#alice", "SK": "SESSION#old", "expiresAt": now - 60})  # already expired
    batch.put_item(Item={"PK": "USER#alice", "SK": "SESSION#new", "expiresAt": now + 3600})
    batch.put_item(Item={"PK": "USER#alice", "SK": "PROFILE"})  # no expiresAt = never expires

# Deletion is a background job (usually within a few days on AWS), so expired
# items can still be returned. Always filter them out on read.
raw = table.query(KeyConditionExpression=Key("PK").eq("USER#alice"))["Items"]
show("Raw query (may include expired items)", [i["SK"] for i in raw])

fresh = table.query(
    KeyConditionExpression=Key("PK").eq("USER#alice"),
    FilterExpression=Attr("expiresAt").not_exists() | Attr("expiresAt").gt(int(time.time())),
)["Items"]
show("Filtered query (live items only)", [i["SK"] for i in fresh])

# Common mistake: milliseconds instead of seconds - the item looks like it
# expires in the year ~58,000, so it is never deleted.
table.put_item(Item={"PK": "USER#alice", "SK": "SESSION#bug", "expiresAt": int(time.time() * 1000)})
show("Milliseconds TTL value (wrong!)", table.get_item(Key={"PK": "USER#alice", "SK": "SESSION#bug"})["Item"])
