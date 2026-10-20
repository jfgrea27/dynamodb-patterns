"""25 - Transactions: all-or-nothing writes across several items."""

from botocore.exceptions import ClientError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import client, recreate_table, show

TABLE = "p25-transactions"
table = recreate_table(TABLE)

table.put_item(Item={"PK": "PRODUCT#widget", "SK": "STOCK", "stock": 3})
table.put_item(Item={"PK": "USER#alice", "SK": "PROFILE", "orderCount": 0})


def place_order(order_id, qty):
    """Create the order, decrement stock and bump the user's counter - atomically.

    `client` is the resource's client, so plain Python values are serialized for us.
    """
    client.transact_write_items(
        TransactItems=[
            {
                "Put": {
                    "TableName": TABLE,
                    "Item": {"PK": "USER#alice", "SK": f"ORDER#{order_id}", "qty": qty},
                    "ConditionExpression": "attribute_not_exists(PK)",
                }
            },
            {
                "Update": {
                    "TableName": TABLE,
                    "Key": {"PK": "PRODUCT#widget", "SK": "STOCK"},
                    "UpdateExpression": "SET stock = stock - :q",
                    "ConditionExpression": "stock >= :q",
                    "ExpressionAttributeValues": {":q": qty},
                }
            },
            {
                "Update": {
                    "TableName": TABLE,
                    "Key": {"PK": "USER#alice", "SK": "PROFILE"},
                    "UpdateExpression": "ADD orderCount :one",
                    "ExpressionAttributeValues": {":one": 1},
                }
            },
        ],
        # Same token within 10 minutes = same transaction, so retries are safe.
        ClientRequestToken=f"place-order-{order_id}",
    )


place_order("o1", 2)
show("Order o1 (qty 2) succeeded")

try:
    place_order("o2", 5)  # only 1 left in stock
except ClientError as e:
    reasons = [r["Code"] for r in e.response.get("CancellationReasons", [])]
    show("Order o2 (qty 5) cancelled - per-item reasons", reasons)

# Nothing from the failed transaction was written: no ORDER#o2, stock and counter unchanged.
resp = client.transact_get_items(
    TransactItems=[
        {"Get": {"TableName": TABLE, "Key": {"PK": "PRODUCT#widget", "SK": "STOCK"}}},
        {"Get": {"TableName": TABLE, "Key": {"PK": "USER#alice", "SK": "PROFILE"}}},
        {"Get": {"TableName": TABLE, "Key": {"PK": "USER#alice", "SK": "ORDER#o2"}}},
    ]
)
show("TransactGetItems: stock, profile, ORDER#o2", [r.get("Item") for r in resp["Responses"]])
