"""05 - Composite / hierarchical sort keys: query any level with begins_with."""

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p05-composite-sk")

# One brand's stores, keyed COUNTRY#STATE#CITY#STORE - most general -> most specific.
stores = [
    ("US", "CA", "San Francisco", "s1"),
    ("US", "CA", "Los Angeles", "s2"),
    ("US", "NY", "New York", "s3"),
    ("UK", "ENG", "London", "s4"),
    ("UK", "ENG", "Manchester", "s5"),
]
with table.batch_writer() as batch:
    for country, state, city, store in stores:
        batch.put_item(Item={
            "PK": "BRAND#acme",
            "SK": f"STORE#{country}#{state}#{city}#{store}",
            "country": country, "state": state, "city": city, "storeId": store,
        })


def stores_under(prefix):
    resp = table.query(
        KeyConditionExpression=Key("PK").eq("BRAND#acme") & Key("SK").begins_with(f"STORE#{prefix}")
    )
    return [f"{i['city']} ({i['storeId']})" for i in resp["Items"]]


show("All stores", stores_under(""))
show("Country = US", stores_under("US#"))
show("State = US/CA", stores_under("US#CA#"))
show("City = London", stores_under("UK#ENG#London#"))

# Composite keys also give range queries on the trailing part, e.g. dates.
with table.batch_writer() as batch:
    for d in ["2026-10-01", "2026-10-10", "2026-10-20", "2026-11-02"]:
        batch.put_item(Item={"PK": "DEVICE#d1", "SK": f"READING#{d}", "temp": 20})
resp = table.query(
    KeyConditionExpression=Key("PK").eq("DEVICE#d1")
    & Key("SK").between("READING#2026-10-05", "READING#2026-10-31")
)
show("Readings 5-31 Oct", [i["SK"] for i in resp["Items"]])
