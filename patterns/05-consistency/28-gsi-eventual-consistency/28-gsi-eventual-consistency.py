"""28 - GSIs are eventually consistent: design for read-after-write gaps."""

import time

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import gsi, recreate_table, show

table = recreate_table("p28-gsi-consistency", gsis=[gsi("GSI1")])

# 1. ConsistentRead is not allowed on a GSI.
try:
    table.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq("EMAIL#a@x.com"), ConsistentRead=True)
except ClientError as e:
    show("ConsistentRead=True on a GSI", e.response["Error"]["Message"])

# 2. Write then immediately read the index. On AWS this can miss the item
#    (usually propagates in well under a second). DynamoDB Local is instant.
table.put_item(Item={"PK": "USER#1", "SK": "PROFILE", "GSI1PK": "EMAIL#a@x.com", "GSI1SK": "USER#1"})
hits = table.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq("EMAIL#a@x.com"))["Count"]
show("Immediate GSI read after write (Local is instant; AWS may return 0)", hits)


# 3. Mitigation A: read the base table by primary key when you need fresh data.
item = table.get_item(Key={"PK": "USER#1", "SK": "PROFILE"}, ConsistentRead=True)["Item"]
show("Strongly consistent read from the base table", item)


# 4. Mitigation B: if you must use the index, retry briefly with backoff.
def query_gsi_until_found(value, attempts=5):
    for i in range(attempts):
        items = table.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq(value))["Items"]
        if items:
            return items, i + 1
        time.sleep(0.05 * 2**i)
    return [], attempts


items, tries = query_gsi_until_found("EMAIL#a@x.com")
show(f"GSI read with retry (found after {tries} attempt(s))", items)

# 5. GSIs don't enforce uniqueness: two items can share GSI1PK. See 26-unique-constraints.
table.put_item(Item={"PK": "USER#2", "SK": "PROFILE", "GSI1PK": "EMAIL#a@x.com", "GSI1SK": "USER#2"})
dupes = table.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq("EMAIL#a@x.com"))["Items"]
show("Two users with the same email in the GSI", [d["PK"] for d in dupes])
