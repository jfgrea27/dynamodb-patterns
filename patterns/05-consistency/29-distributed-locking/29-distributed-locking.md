# 29 · Distributed locking

**Run:** `just run 29`

## Problem

Several workers or instances must not do the same job at the same time (a nightly invoice run, a migration, processing one customer's queue). You need a lock that every machine can see.

## Pattern

The lock is an item. You **acquire** it with a conditional put that succeeds only if the lock doesn't exist or its lease has expired. You **release** it with a conditional delete that succeeds only if you still own it.

| PK                 | SK     | owner    | expiresAt (epoch) |
|--------------------|--------|----------|-------------------|
| `LOCK#invoice-run` | `LOCK` | worker-A | 1792494214        |

```python
# acquire
put_item(Item=lock,
         ConditionExpression="attribute_not_exists(PK) OR expiresAt < :now")
# heartbeat (extend lease)
update_item(SET expiresAt = :later, ConditionExpression="owner = :me")
# release
delete_item(ConditionExpression="owner = :me")
```

The script shows:

1. A acquires the lock, and B is refused.
2. A heartbeats, then releases; B acquires.
3. B crashes without releasing. After the lease expires, C takes over.
4. "Zombie" B tries to release C's lock and is refused.

## Why

- **No extra infrastructure.** No Redis, ZooKeeper or etcd to run.
- **Crash-safe.** The lease means a dead holder can't block everyone forever.
- **Safe release.** The owner check stops one worker from deleting another's lock.

## Trade-offs

- **Leases depend on clocks.** A paused process (GC pause, slow network) can wake up after its lease expired and *think* it still holds the lock. Holders must heartbeat well before expiry and stop work if a heartbeat fails.
- For strict safety, use a **fencing token**: a number that increases on every acquisition (e.g. `ADD fencingToken :1` on an item that is never deleted). The protected resource then rejects writes carrying an older token.
- Each acquire, heartbeat and release costs a write. That's fine for coarse locks, but not for millisecond-level locks.

## Gotchas

- Also set `expiresAt` as the table's TTL attribute ([30](../../06-lifecycle-and-events/30-ttl-expiry/30-ttl-expiry.md)) so abandoned lock items get cleaned up. Don't rely on TTL for correctness, though: deletion can lag by hours. The `expiresAt < :now` condition is what makes takeover work.
- The ready-made library is the [DynamoDB Lock Client](https://github.com/awslabs/amazon-dynamodb-lock-client) (Java). In Python, `python-dynamodb-lock` follows the same design.
- Related: [22 conditional writes](../22-conditional-writes/22-conditional-writes.md), [23 optimistic locking](../23-optimistic-locking/23-optimistic-locking.md). Prefer optimistic locking if you only need to protect a single item.
