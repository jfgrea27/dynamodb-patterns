# 40 · Global tables (multi-region)

**Run:** `just run 40`

## Problem

Users are spread across continents, and cross-region latency adds 100+ ms per request. Or you need to survive a whole AWS region going down. A single-region table can't do either.

## Pattern

Make the table a **global table**: a fully managed replica in every chosen region. Each replica accepts reads **and writes** (active-active). DynamoDB replicates changes between regions asynchronously, usually in about a second.

```python
client.update_table(
    TableName="orders",
    ReplicaUpdates=[{"Create": {"RegionName": "eu-west-1"}}],
)
```

Conflicts (the same item written in two regions before replication catches up) are resolved by **last writer wins**, using an internal timestamp. The losing write is discarded with no error.

DynamoDB Local doesn't support replicas, so the script simulates two regions with dicts. It shows:

1. A write in one region becomes visible in the other after replication.
2. A conflict where `CANCELLED` is silently overwritten by a later `SHIPPED`.
3. The fix: each item has a **home region** and is only written there.

## Why

- **Low latency.** Users read and write in their nearest region.
- **High availability.** 99.999% SLA. If a region fails, route traffic to another.
- **Fully managed.** No replication code to write or run.

## Trade-offs

- **Cross-region reads are eventually consistent.** Strong reads only see writes made in the same region.
- **Last-writer-wins can lose data.** Avoid concurrent writes to one item from several regions by giving items a home region ("write locally, read globally"). Conditional writes and transactions are only checked in the region where they run.
- **Cost.** You pay for replicated writes in every region, plus cross-region data transfer.
- **Multi-Region strong consistency (MRSC)** is available as an option. Writes are synchronously replicated across 3 regions, which removes the conflicts, at the cost of higher write latency and some limits (e.g. no transactions).

## Gotchas

- All replicas must have the same key schema, GSIs, and TTL and stream settings. Changes are made once and applied everywhere.
- Counters ([24](../../05-consistency/24-atomic-counters/24-atomic-counters.md)) and optimistic locking ([23](../../05-consistency/23-optimistic-locking/23-optimistic-locking.md)) are only safe if all writes for an item go to one region.
- TTL deletes ([30](../../06-lifecycle-and-events/30-ttl-expiry/30-ttl-expiry.md)) replicate too, and consume write capacity in the replica regions.
- Use the current version (2019.11.21). The legacy 2017 version needs a manual migration.
