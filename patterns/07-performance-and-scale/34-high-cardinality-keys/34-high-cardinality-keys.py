"""34 - High-cardinality partition keys: pick a PK with many distinct values."""

import random
from collections import Counter

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import gsi, recreate_table, show

table = recreate_table("p34-high-cardinality", gsis=[gsi("GSI1")])

STATUSES = ["PENDING", "SHIPPED", "DELIVERED"]
orders = [{"order_id": f"o{i:04d}", "customer": f"c{random.randrange(300):03d}", "status": random.choice(STATUSES)} for i in range(1000)]

# BAD key choice: PK=status -> only 3 partition key values, so all traffic piles onto 3 partitions.
bad = Counter(o["status"] for o in orders)
show("BAD: PK=status -> distinct partition keys", {"distinct": len(bad), "items_per_key": dict(bad)})

# GOOD: PK=order id (or customer id). Thousands of keys hash evenly across partitions.
with table.batch_writer() as batch:
    for o in orders:
        batch.put_item(
            Item={
                "PK": f"CUSTOMER#{o['customer']}",
                "SK": f"ORDER#{o['order_id']}",
                "status": o["status"],
                # If you really need "by status", index it on a GSI ...and the GSI has the same
                # cardinality problem, so add a shard suffix (see 35-write-sharding).
                "GSI1PK": f"STATUS#{o['status']}#{int(o['order_id'][1:]) % 4}",
                "GSI1SK": f"ORDER#{o['order_id']}",
            }
        )

good = Counter(f"CUSTOMER#{o['customer']}" for o in orders)
show("GOOD: PK=customer -> distinct partition keys", {"distinct": len(good), "max_items_on_one_key": max(good.values())})

customer = orders[0]["customer"]
resp = table.query(KeyConditionExpression=Key("PK").eq(f"CUSTOMER#{customer}"))
show(f"Orders for CUSTOMER#{customer}", [i["SK"] for i in resp["Items"]])

# "Pending orders" via the sharded GSI: query each shard and merge.
pending = []
for shard in range(4):
    pending += table.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq(f"STATUS#PENDING#{shard}"))["Items"]
show("PENDING orders via sharded GSI", len(pending))
