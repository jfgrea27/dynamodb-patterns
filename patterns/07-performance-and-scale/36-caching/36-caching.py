"""36 - Caching: read-through / write-through cache in front of hot keys (DAX stand-in)."""

import time

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p36-caching")
table.put_item(Item={"PK": "PRODUCT#p1", "SK": "META", "name": "Widget", "price": 10})


class ReadThroughCache:
    """Tiny in-process stand-in for DAX / ElastiCache. Item cache keyed by primary key, with TTL."""

    def __init__(self, table, ttl_seconds=5):
        self.table, self.ttl = table, ttl_seconds
        self.store, self.hits, self.misses = {}, 0, 0

    def get(self, key):
        k = (key["PK"], key["SK"])
        hit = self.store.get(k)
        if hit and hit[1] > time.monotonic():
            self.hits += 1
            return hit[0]
        self.misses += 1
        item = self.table.get_item(Key=key).get("Item")
        self.store[k] = (item, time.monotonic() + self.ttl)
        return item

    def put(self, item):
        # Write-through: update DynamoDB, then the cache, so readers don't see stale data from this writer.
        self.table.put_item(Item=item)
        self.store[(item["PK"], item["SK"])] = (item, time.monotonic() + self.ttl)


cache = ReadThroughCache(table, ttl_seconds=0.5)
key = {"PK": "PRODUCT#p1", "SK": "META"}

for _ in range(100):
    cache.get(key)
show("100 reads of a hot key", {"dynamodb_reads": cache.misses, "cache_hits": cache.hits})

# Writes from *another* process bypass this cache -> stale until TTL expires.
table.update_item(Key=key, UpdateExpression="SET price = :p", ExpressionAttributeValues={":p": 12})
show("Right after an external update (stale)", {"price": cache.get(key)["price"]})
time.sleep(0.6)
show("After TTL expiry (fresh)", {"price": cache.get(key)["price"]})

cache.put({**key, "name": "Widget", "price": 15})
show("After write-through", {"price": cache.get(key)["price"]})
