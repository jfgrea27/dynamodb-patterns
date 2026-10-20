"""14 - Pagination with LastEvaluatedKey, exposed to clients as an opaque cursor."""

import base64
import json

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p14-pagination")

with table.batch_writer() as batch:
    for i in range(23):
        batch.put_item(Item={"PK": "FEED#news", "SK": f"POST#{i:03d}", "title": f"Post {i}"})


def encode_cursor(last_key):
    return base64.urlsafe_b64encode(json.dumps(last_key).encode()).decode() if last_key else None


def decode_cursor(cursor):
    return json.loads(base64.urlsafe_b64decode(cursor)) if cursor else None


def list_posts(cursor=None, page_size=10):
    """What an API handler looks like: cursor in, items + next cursor out."""
    kwargs = {"KeyConditionExpression": Key("PK").eq("FEED#news"), "Limit": page_size}
    start = decode_cursor(cursor)
    if start:
        # In real code: check the decoded key belongs to this PK (don't trust clients).
        if start.get("PK") != "FEED#news":
            raise ValueError("invalid cursor")
        kwargs["ExclusiveStartKey"] = start
    resp = table.query(**kwargs)
    return {
        "items": [i["title"] for i in resp["Items"]],
        "nextCursor": encode_cursor(resp.get("LastEvaluatedKey")),
    }


cursor, page_no = None, 1
while True:
    page = list_posts(cursor)
    show(f"Page {page_no}", page)
    cursor = page["nextCursor"]
    if not cursor:
        break
    page_no += 1

# boto3 paginators do the LastEvaluatedKey loop for you.
paginator = table.meta.client.get_paginator("query")
pages = paginator.paginate(
    TableName=table.name,
    KeyConditionExpression="PK = :pk",
    ExpressionAttributeValues={":pk": "FEED#news"},
    PaginationConfig={"PageSize": 10},
)
show("Paginator page sizes", [p["Count"] for p in pages])
