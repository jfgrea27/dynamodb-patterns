# 35 · Write sharding

**Run:** `just run 35`

## Problem

Every write goes to one partition key, such as "today's events" (`EVENTS#2026-10-20`). A single partition handles about **1,000 WCU and 3,000 RCU per second**. Above that you get throttled, however much table capacity you have. Adaptive capacity helps, but it can't split traffic for a single key.

## Pattern

Add a suffix to the hot key so writes spread over N partitions. On read, query all N and merge the results (**scatter-gather**).

| PK                       | SK          |
|--------------------------|-------------|
| `EVENTS#2026-10-20#0`    | `EVT#00017` |
| `EVENTS#2026-10-20#1`    | `EVT#00003` |
| …                        | …           |
| `EVENTS#2026-10-20#9`    | `EVT#00199` |

There are two ways to pick the suffix:

- **Random suffix** (`random % N`). Writes spread best. To read one item you must query every shard.
- **Calculated suffix** (`hash(order_id) % N`). Writes still spread well. If you know the ID you can work out the shard and do a direct `GetItem`.

## Why

- Write throughput grows roughly N times for that logical key.
- It's the standard fix for time-bucketed keys, global leaderboards, vote counters and similar hot keys.

## Trade-offs

- Reads that need "all of today" cost N queries. Run them in parallel.
- Sorting across shards happens in the client, as a merge.
- Changing N later means old and new data use different shard counts. Store N, or version it.

## Gotchas

- Don't shard by default. First fix the key so it has high cardinality ([34-high-cardinality-keys](../34-high-cardinality-keys/34-high-cardinality-keys.md)). Shard only keys that are truly hot.
- Hot *reads* are often better solved with a cache ([36-caching](../36-caching/36-caching.md)) than with sharding.
- For counters, shard the counter items and sum them on read (see [24-atomic-counters](../../05-consistency/24-atomic-counters/24-atomic-counters.md)).
