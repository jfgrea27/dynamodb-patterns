"""07 - Inverted index: a GSI with PK and SK swapped, to query relationships from the other side."""

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import gsi, recreate_table, show

table = recreate_table("p07-inverted-index", gsis=[gsi("Inverted", pk="SK", sk="PK")])

# Invoices belong to a customer and contain products.
# Base table: "what's on invoice X?". Inverted: "which invoices contain product Y?"
lines = [
    ("INV#1001", "PRODUCT#apple", 3),
    ("INV#1001", "PRODUCT#pear", 1),
    ("INV#1002", "PRODUCT#apple", 5),
    ("INV#1003", "PRODUCT#plum", 2),
]
with table.batch_writer() as batch:
    batch.put_item(Item={"PK": "INV#1001", "SK": "CUSTOMER#c1", "type": "InvoiceCustomer"})
    batch.put_item(Item={"PK": "INV#1002", "SK": "CUSTOMER#c1", "type": "InvoiceCustomer"})
    batch.put_item(Item={"PK": "INV#1003", "SK": "CUSTOMER#c2", "type": "InvoiceCustomer"})
    for inv, product, qty in lines:
        batch.put_item(Item={"PK": inv, "SK": product, "type": "Line", "qty": qty})

resp = table.query(KeyConditionExpression=Key("PK").eq("INV#1001"))
show("Base table: everything on INV#1001", [(i["SK"], i.get("qty")) for i in resp["Items"]])

resp = table.query(IndexName="Inverted", KeyConditionExpression=Key("SK").eq("PRODUCT#apple"))
show("Inverted: invoices containing apple", [(i["PK"], i["qty"]) for i in resp["Items"]])

resp = table.query(IndexName="Inverted", KeyConditionExpression=Key("SK").eq("CUSTOMER#c1"))
show("Inverted: invoices for customer c1", [i["PK"] for i in resp["Items"]])
