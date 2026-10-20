"""17 - Keep items small: unbounded lists become separate items in an item collection."""

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p17-small-items")

# BAD: comments appended to a list on the post item. Every append rewrites the
# whole item (WCUs scale with item size) and eventually hits the 400 KB limit.
table.put_item(Item={"PK": "POST#p1", "SK": "POST", "title": "Hello", "comments": []})
for i in range(50):
    table.update_item(
        Key={"PK": "POST#p1", "SK": "POST"},
        UpdateExpression="SET comments = list_append(comments, :c)",
        ExpressionAttributeValues={":c": [{"by": f"user{i}", "text": "Nice post! " * 20}]},
    )
resp = table.get_item(Key={"PK": "POST#p1", "SK": "POST"}, ReturnConsumedCapacity="TOTAL")
show("BAD: one big item - read cost for just the title", resp["ConsumedCapacity"])

# GOOD: the post is small. Each comment is its own item in the same collection.
table.put_item(Item={"PK": "POST#p2", "SK": "POST", "title": "Hello", "comment_count": 50})
with table.batch_writer() as batch:
    for i in range(50):
        batch.put_item(Item={"PK": "POST#p2", "SK": f"COMMENT#2026-10-20T10:{i:02d}", "by": f"user{i}", "text": "Nice post! " * 20})

resp = table.get_item(Key={"PK": "POST#p2", "SK": "POST"}, ReturnConsumedCapacity="TOTAL")
show("GOOD: post only - read cost", resp["ConsumedCapacity"])

# Latest 5 comments, without reading the other 45
resp = table.query(
    KeyConditionExpression=Key("PK").eq("POST#p2") & Key("SK").begins_with("COMMENT#"),
    ScanIndexForward=False,
    Limit=5,
    ReturnConsumedCapacity="TOTAL",
)
show("GOOD: latest 5 comments", {"count": resp["Count"], "consumed": resp["ConsumedCapacity"], "first": resp["Items"][0]["SK"]})
