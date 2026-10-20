# 36 · Caching (DAX / ElastiCache)

**Run:** `just run 36`

## Problem

Some keys are read far more than others: a product page, a config item, a celebrity profile. One partition serves at most ~3,000 RCU/s. Paying for the same read over and over is also wasteful.

## Pattern

Put a cache in front of DynamoDB.

- **DAX (DynamoDB Accelerator):** a managed, API-compatible cache. Swap the client and keep the same calls. Microsecond reads. It has an item cache (GetItem/BatchGetItem) and a query cache (Query/Scan).
- **ElastiCache / Redis:** more control, e.g. caching computed views across several items. You manage invalidation.

Common strategies:

| Strategy        | Read                                  | Write                                 |
|-----------------|---------------------------------------|---------------------------------------|
| Read-through    | cache miss → read DynamoDB → fill cache | write to DynamoDB only               |
| Write-through   | from cache                            | write DynamoDB, then update cache     |
| TTL             | entries expire after N seconds        | n/a, bounds how stale data can get    |

The script uses an in-process dict as a stand-in. DynamoDB Local has no DAX. With real DAX:

```python
from amazondax import AmazonDaxClient
dax = AmazonDaxClient.resource(endpoint_url="daxs://my-cluster.xxxx.dax-clusters.us-east-1.amazonaws.com")
table = dax.Table("my-table")          # same API as boto3
table.get_item(Key={"PK": "PRODUCT#p1", "SK": "META"})
```

## Why

- Takes read load off hot partitions.
- Much lower latency. Cheaper when the hit rate is high.

## Trade-offs

- **Stale reads.** DAX is eventually consistent. Strongly consistent reads skip the cache. Writes from other clients aren't seen until the TTL expires.
- Another piece of infrastructure (a cluster in a VPC) to run and pay for.
- No help for write-heavy keys (see [35-write-sharding](../35-write-sharding/35-write-sharding.md)).

## Gotchas

- In DAX the item cache and the query cache are separate. A write updates the item cache but **not** cached query results.
- Short TTLs bound staleness but lower the hit rate. Tune them for each kind of data.
- Before adding a cache, check whether a better key design ([34-high-cardinality-keys](../34-high-cardinality-keys/34-high-cardinality-keys.md)) or [11-denormalization](../../02-modelling/11-denormalization/11-denormalization.md) removes the hot read.
