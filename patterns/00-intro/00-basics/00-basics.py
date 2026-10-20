"""00 - Basics: create a table, then the core item operations (put, get, update, query, delete)."""

import sys
from pathlib import Path

from boto3.dynamodb.conditions import Key

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

# Table with a composite primary key: partition key PK + sort key SK.
table = recreate_table("p00-basics")

# PutItem: create (or fully replace) an item. Attributes beyond the key are free-form.
table.put_item(Item={"PK": "ANIMAL#dog", "SK": "Rex", "age": 4, "breed": "labrador", "tags": {"good", "loud"}})
table.put_item(Item={"PK": "ANIMAL#dog", "SK": "Bella", "age": 2})
table.put_item(Item={"PK": "ANIMAL#cat", "SK": "Tom", "age": 7, "owner": {"name": "Sam", "city": "Leeds"}})

# GetItem: fetch exactly one item by its full primary key.
show("GetItem Rex", table.get_item(Key={"PK": "ANIMAL#dog", "SK": "Rex"})["Item"])

# GetItem on a missing key returns no "Item" (not an error).
show("GetItem missing key", "Item" in table.get_item(Key={"PK": "ANIMAL#dog", "SK": "Nope"}))

# UpdateItem: change some attributes, leave the rest. ReturnValues shows the result.
resp = table.update_item(
    Key={"PK": "ANIMAL#dog", "SK": "Rex"},
    UpdateExpression="SET age = age + :one, last_vet = :d REMOVE breed",
    ExpressionAttributeValues={":one": 1, ":d": "2026-10-20"},
    ReturnValues="ALL_NEW",
)
show("UpdateItem Rex (age+1, set last_vet, remove breed)", resp["Attributes"])

# Query: all items for one partition key, sorted by sort key.
show("Query all dogs", table.query(KeyConditionExpression=Key("PK").eq("ANIMAL#dog"))["Items"])

# Query with a sort key condition, newest-first style (descending SK).
resp = table.query(
    KeyConditionExpression=Key("PK").eq("ANIMAL#dog") & Key("SK").begins_with("R"),
    ScanIndexForward=False,
)
show("Query dogs whose name starts with R", resp["Items"])

# Conditional write: only create if it doesn't already exist.
try:
    table.put_item(Item={"PK": "ANIMAL#dog", "SK": "Rex", "age": 0}, ConditionExpression="attribute_not_exists(PK)")
except table.meta.client.exceptions.ConditionalCheckFailedException:
    show("Conditional put rejected", "Rex already exists, nothing was overwritten")

# DeleteItem: remove by primary key, returning what was deleted.
resp = table.delete_item(Key={"PK": "ANIMAL#cat", "SK": "Tom"}, ReturnValues="ALL_OLD")
show("DeleteItem Tom (old value)", resp["Attributes"])

# Scan: reads the whole table. Fine for a demo, avoid in real request paths.
show("Scan (whole table)", table.scan()["Items"])
