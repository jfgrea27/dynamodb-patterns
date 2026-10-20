"""42 - Anti-patterns: see what each one costs, using ConsumedCapacity and request counts."""

from collections import Counter

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import gsi, recreate_table, show

# ---------------------------------------------------------------------------
# 1. Relational modeling: one table per entity, joins in app code (N+1 requests)
# ---------------------------------------------------------------------------
users = recreate_table("p42-users", pk="userId", sk=None)
orders = recreate_table("p42-orders", pk="orderId", sk=None)
users.put_item(Item={"userId": "u1", "name": "Alice", "orderIds": ["o1", "o2", "o3"]})
for oid in ("o1", "o2", "o3"):
    orders.put_item(Item={"orderId": oid, "userId": "u1", "total": 10})

requests = 1
user = users.get_item(Key={"userId": "u1"})["Item"]
for oid in user["orderIds"]:
    orders.get_item(Key={"orderId": oid})
    requests += 1

single = recreate_table("p42-single")
single.put_item(Item={"PK": "USER#u1", "SK": "PROFILE", "name": "Alice"})
for oid in ("o1", "o2", "o3"):
    single.put_item(Item={"PK": "USER#u1", "SK": f"ORDER#{oid}", "total": 10})
single.query(KeyConditionExpression=Key("PK").eq("USER#u1"))
show("1. Relational modeling: requests to load a user + orders", {"table-per-entity": requests, "single-table": 1})

# ---------------------------------------------------------------------------
# 2. Unbounded list inside one item: every append rewrites the whole item, then it hits 400 KB
# ---------------------------------------------------------------------------
t = recreate_table("p42-unbounded")
t.put_item(Item={"PK": "CHAT#c1", "SK": "META", "messages": []})
wcu = []
try:
    for i in range(100):
        resp = t.update_item(
            Key={"PK": "CHAT#c1", "SK": "META"},
            UpdateExpression="SET messages = list_append(messages, :m)",
            ExpressionAttributeValues={":m": [f"message {i} " + "x" * 10_000]},
            ReturnConsumedCapacity="TOTAL",
        )
        wcu.append(resp["ConsumedCapacity"]["CapacityUnits"])
    show("2. Unbounded list: never failed?!")
except ClientError as e:
    show(
        "2. Unbounded list",
        {
            "appends before failure": len(wcu),
            "WCU of 1st / last append": [wcu[0], wcu[-1]],
            "error": e.response["Error"]["Message"],
            "fix": "one item per message: PK=CHAT#c1, SK=MSG#<ulid> (patterns 17, 06)",
        },
    )

# ---------------------------------------------------------------------------
# 3. Low-cardinality partition key: everything lands on a handful of partitions
# ---------------------------------------------------------------------------
t = recreate_table("p42-low-cardinality")
statuses = ["PENDING"] * 900 + ["SHIPPED"] * 90 + ["CANCELLED"] * 10
with t.batch_writer() as w:
    for i, s in enumerate(statuses):
        w.put_item(Item={"PK": f"STATUS#{s}", "SK": f"ORDER#{i:04}"})
show(
    "3. Low-cardinality PK (PK=status): items per partition key",
    {**Counter(statuses), "note": "90% of reads/writes hit one key -> ~1,000 WCU/s cap. Use PK=ORDER#id + sparse GSI (10) or sharding (35)"},
)

# ---------------------------------------------------------------------------
# 4. Scan + filter instead of a key query: you pay for everything scanned
# ---------------------------------------------------------------------------
t = recreate_table("p42-scan-filter", gsis=[gsi("GSI1")])
with t.batch_writer() as w:
    for i in range(1000):
        item = {"PK": f"ORDER#{i:04}", "SK": "META", "customer": f"C{i % 100}", "pad": "x" * 500}
        item |= {"GSI1PK": item["customer"], "GSI1SK": item["PK"]}
        w.put_item(Item=item)

scanned = consumed = matched = 0
kwargs = dict(FilterExpression=Attr("customer").eq("C7"), ReturnConsumedCapacity="TOTAL")
while True:
    resp = t.scan(**kwargs)
    scanned += resp["ScannedCount"]
    matched += resp["Count"]
    consumed += resp["ConsumedCapacity"]["CapacityUnits"]
    if "LastEvaluatedKey" not in resp:
        break
    kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

q = t.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq("C7"), ReturnConsumedCapacity="TOTAL")
show(
    "4. Scan+filter vs Query on a GSI (find one customer's orders)",
    {
        "scan":  {"scanned": scanned, "returned": matched, "RCU": consumed},
        "query": {"scanned": q["ScannedCount"], "returned": q["Count"], "RCU": q["ConsumedCapacity"]["CapacityUnits"]},
    },
)

# ---------------------------------------------------------------------------
# 5. Too many GSIs: every write is repeated into each index that has the key attributes
# ---------------------------------------------------------------------------
def write_cost(n_gsis):
    t = recreate_table(f"p42-gsis-{n_gsis}", gsis=[gsi(f"GSI{i}") for i in range(n_gsis)])
    item = {"PK": "X", "SK": "Y", "pad": "x" * 900}
    for i in range(n_gsis):
        item |= {f"GSI{i}PK": "a", f"GSI{i}SK": "b"}
    resp = t.put_item(Item=item, ReturnConsumedCapacity="INDEXES")
    return resp["ConsumedCapacity"]["CapacityUnits"]


show("5. WCU for one ~1 KB put", {f"{n} GSIs": write_cost(n) for n in (0, 2, 5)})

# ---------------------------------------------------------------------------
# 6. Ad-hoc analytics on the live table
# ---------------------------------------------------------------------------
show(
    "6. Ad-hoc analytics on DynamoDB",
    "GROUP BY / joins / 'top N by X' need a full scan every time (see #4) and steal capacity "
    "from live traffic. Export to S3 + Athena, or zero-ETL to Redshift instead (pattern 41).",
)
