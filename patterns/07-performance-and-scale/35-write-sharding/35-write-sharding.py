"""35 - Write sharding: spread a hot partition key across N suffixed keys, scatter-gather on read."""

import hashlib
import random
from concurrent.futures import ThreadPoolExecutor

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p35-write-sharding")

SHARDS = 10
DAY = "2026-10-20"

# --- Random suffix: best write spread, but reads must hit every shard. ---
with table.batch_writer() as batch:
    for i in range(200):
        shard = random.randrange(SHARDS)
        batch.put_item(Item={"PK": f"EVENTS#{DAY}#{shard}", "SK": f"EVT#{i:05d}", "kind": random.choice(["click", "view"])})


def query_shard(shard):
    resp = table.query(KeyConditionExpression=Key("PK").eq(f"EVENTS#{DAY}#{shard}"))
    return resp["Items"]


# Scatter-gather: query all shards in parallel, merge the results.
with ThreadPoolExecutor(max_workers=SHARDS) as pool:
    results = list(pool.map(query_shard, range(SHARDS)))
show("Random suffix: items per shard", {f"shard {i}": len(r) for i, r in enumerate(results)})
show("Total gathered", sum(len(r) for r in results))


# --- Calculated suffix: derive the shard from a known attribute so single-item reads stay O(1). ---
def shard_for(order_id: str) -> int:
    return int(hashlib.md5(order_id.encode()).hexdigest(), 16) % SHARDS


for oid in ["o-1001", "o-1002", "o-1003"]:
    table.put_item(Item={"PK": f"ORDERS#{DAY}#{shard_for(oid)}", "SK": f"ORDER#{oid}", "total": 10})

oid = "o-1002"
item = table.get_item(Key={"PK": f"ORDERS#{DAY}#{shard_for(oid)}", "SK": f"ORDER#{oid}"})["Item"]
show(f"Calculated suffix: direct GetItem for {oid} (shard {shard_for(oid)})", item)
