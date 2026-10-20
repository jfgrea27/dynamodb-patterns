"""24 - Atomic counters: increment in place with UpdateItem ADD."""

from concurrent.futures import ThreadPoolExecutor

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p24-atomic-counters")
KEY = {"PK": "POST#hello-world", "SK": "STATS"}


def increment(_):
    # ADD creates the attribute (starting at 0) if missing. No read needed.
    table.update_item(
        Key=KEY,
        UpdateExpression="ADD #v :one",
        ExpressionAttributeNames={"#v": "views"},  # "views" is a reserved word
        ExpressionAttributeValues={":one": 1},
    )


# 50 concurrent increments - none get lost, unlike read-modify-write.
with ThreadPoolExecutor(max_workers=10) as pool:
    list(pool.map(increment, range(50)))
show("After 50 concurrent increments", table.get_item(Key=KEY)["Item"])

# Read-modify-write (the anti-pattern) loses updates under concurrency.
table.put_item(Item={**KEY, "views": 0})


def racy_increment(_):
    current = table.get_item(Key=KEY)["Item"]["views"]
    table.put_item(Item={**KEY, "views": current + 1})


with ThreadPoolExecutor(max_workers=10) as pool:
    list(pool.map(racy_increment, range(50)))
show("Racy read-modify-write after 50 'increments' (expect < 50)", table.get_item(Key=KEY)["Item"])

# Return the new value in the same call, e.g. to hand out sequence numbers.
resp = table.update_item(
    Key={"PK": "SEQUENCE#invoice", "SK": "COUNTER"},
    UpdateExpression="ADD #n :one",
    ExpressionAttributeNames={"#n": "next"},
    ExpressionAttributeValues={":one": 1},
    ReturnValues="UPDATED_NEW",
)
show("Next invoice number", resp["Attributes"])

# Bounded counter: refuse to go below zero.
table.put_item(Item={"PK": "TICKETS#gig", "SK": "COUNTER", "remaining": 1})
for attempt in range(2):
    try:
        table.update_item(
            Key={"PK": "TICKETS#gig", "SK": "COUNTER"},
            UpdateExpression="ADD remaining :minus",
            ConditionExpression="remaining > :zero",
            ExpressionAttributeValues={":minus": -1, ":zero": 0},
        )
        show(f"Ticket sale {attempt + 1}: sold")
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        show(f"Ticket sale {attempt + 1}: sold out")
