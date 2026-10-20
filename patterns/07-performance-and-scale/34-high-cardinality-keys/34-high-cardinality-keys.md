# 34 · High-cardinality partition keys

**Run:** `just run 34`

## Problem

DynamoDB hashes the partition key to choose a physical partition. If the key has only a few distinct values (`status`, `country`, `date`, `tenant` when one tenant is huge), traffic piles onto a few partitions. Those partitions get throttled while the rest of the table sits idle.

## Pattern

Choose a partition key with **many distinct values that are used about evenly**. Good examples are user ID, order ID, device ID and session ID.

| Choice           | Distinct values | Verdict |
|------------------|-----------------|---------|
| `status`         | 3               | ❌ hot partitions |
| `date`           | 1 per day       | ❌ today's partition gets all writes |
| `customerId`     | 100k+           | ✅ |
| `orderId`        | millions        | ✅ |

If you need to query by a low-cardinality attribute, put it in a GSI. GSIs have the same per-partition limits, so shard the GSI key too ([35-write-sharding](../35-write-sharding/35-write-sharding.md)) or make it sparse ([10-sparse-index](../../02-modelling/10-sparse-index/10-sparse-index.md)).

## Why

- Throughput is spread evenly across partitions, so the table's capacity is usable.
- You avoid throttling that only shows up under load.

## Trade-offs

- A high-cardinality key often means a query "by status" needs a GSI, or a different design.
- Item collections (data stored together) are smaller, so pick the key that is both spread out and matches how you read the data ([02-access-pattern-first](../../02-modelling/02-access-pattern-first/02-access-pattern-first.md)).

## Gotchas

- What counts is *uneven traffic*, not just the number of distinct values. A million users where one celebrity gets 90% of traffic is still a hot key.
- Use CloudWatch Contributor Insights to find hot keys in production.
- Throttling on a GSI also throttles writes to the base table.
