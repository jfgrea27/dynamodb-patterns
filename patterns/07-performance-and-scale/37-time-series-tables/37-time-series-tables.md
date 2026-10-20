# 37 · Time-series tables

**Run:** `just run 37`

## Problem

Time-series data (metrics, events, logs) has three traits:

- Writes all go to "now". A `date` partition key gets hot.
- Recent data is read a lot. Old data is almost never read.
- Old data must be deleted. Deleting item by item costs a write unit per item.

## Pattern

**Option A: one table per period** (day, week or month).

| Table                  | Status                                        |
|------------------------|-----------------------------------------------|
| `metrics-2026-10`      | current: high write capacity                  |
| `metrics-2026-09`      | read-only: low capacity                       |
| `metrics-2026-08`      | expired: **drop the table** (free, instant)   |

Create next period's table ahead of time. Point writers at the current table. Drop whole tables when they pass retention.

**Option B: one table, time-bucketed partition key, plus TTL** ([30-ttl-expiry](../../06-lifecycle-and-events/30-ttl-expiry/30-ttl-expiry.md)).

| PK                      | SK                          | value | expires_at |
|-------------------------|-----------------------------|-------|------------|
| `SENSOR#s1#2026-10-20`  | `2026-10-20T01:20:00+00:00` | 80    | 1763600400 |

The bucket (sensor + day) keeps partitions bounded and spreads writes. The ISO timestamp in the sort key gives range queries (`between`).

## Why

- **A:** Dropping a table costs nothing and takes no write capacity. Each period can be tuned separately (capacity, table class, e.g. Standard-IA for old tables).
- **B:** Simpler to run: one table, one schema. TTL deletes are free (no WCU).

## Trade-offs

- **A:** The app must route requests to the right table. A query across periods hits several tables. You need automation to create and drop tables.
- **B:** TTL deletes are not instant (see Gotchas). Too fine a bucket means many queries for a long range. Too coarse a bucket gets hot.

## Gotchas

- TTL deletes usually happen within a few days of expiry, not at the moment of expiry. Filter out `expires_at < now` on read if it matters.
- DynamoDB Local accepts the TTL setting, but don't rely on it to delete items on schedule.
- For heavy writes, combine the bucket with a shard suffix ([35-write-sharding](../35-write-sharding/35-write-sharding.md)).
- For analytics over history, export to S3 instead ([41-analytics-export](../../08-operations/41-analytics-export/41-analytics-export.md)).
