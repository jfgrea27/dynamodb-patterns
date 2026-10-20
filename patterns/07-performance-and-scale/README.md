# 07 · Performance & scale

DynamoDB scales by spreading data across partitions, and each partition has a throughput ceiling (about 3,000 reads and 1,000 writes per second). Performance problems almost always mean **too much traffic on too few partition key values**. This section covers spreading load, caching hot reads and handling data that piles up over time.

## Key ideas

- **High-cardinality partition keys** (user ID, order ID) spread traffic naturally. Low-cardinality ones (status, date, country) create hot partitions.
- **Write sharding** splits one hot logical key into `KEY#0..N`, either with random suffixes plus a scatter-gather read, or with calculated suffixes so you can still do a direct get.
- **Caching** (DAX or a read-through cache) absorbs repeated reads of the same hot items, at the cost of staleness.
- **Time-series data** is usually written to "now" and read recently. Bucket keys by time, expire old data with TTL, or rotate a table per period.

## Lessons

| # | Lesson | You'll learn |
|---|---|---|
| 34 | [High-cardinality partition keys](34-high-cardinality-keys/34-high-cardinality-keys.md) | Measuring key distribution; moving low-cardinality lookups to a GSI |
| 35 | [Write sharding](35-write-sharding/35-write-sharding.md) | Random vs calculated shard suffixes, parallel reads |
| 36 | [Caching (DAX / ElastiCache)](36-caching/36-caching.md) | Read-through and write-through caching, hit rates, staleness |
| 37 | [Time-series tables](37-time-series-tables/37-time-series-tables.md) | Table-per-period rotation vs time-bucketed keys with TTL |

**Before:** [06-lifecycle-and-events](../06-lifecycle-and-events/README.md) · **Next:** [08-operations](../08-operations/README.md)
