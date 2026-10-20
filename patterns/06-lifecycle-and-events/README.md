# 06 · Lifecycle & events

What happens to data over time, and how to react when it changes. **TTL** expires items for free. **DynamoDB Streams** delivers an ordered log of every insert, update and delete, which you can use to keep other systems and derived data in sync.

## Key ideas

- **TTL** deletes items after an epoch-seconds timestamp, at no write cost. Deletion is lazy (it can take hours to days), so filter out expired items on read.
- **Streams are change data capture.** Each change carries the old and/or new image, delivered in order per item for 24 hours. A Lambda (or other consumer) projects changes into search indexes, caches, analytics or other tables.
- **Aggregates via streams.** Instead of counting at read time, apply each change as a delta to a running total. Reads become a single `GetItem`.
- **Soft delete, then archive.** Mark the item deleted (and drop it out of sparse indexes), let TTL remove it, and let the stream's REMOVE event copy it to S3.

## Lessons

| # | Lesson | You'll learn |
|---|---|---|
| 30 | [TTL for expiry](30-ttl-expiry/30-ttl-expiry.md) | Enabling TTL, filtering expired items, the milliseconds bug |
| 31 | [Streams / CDC](31-streams-cdc/31-streams-cdc.md) | Reading a stream and projecting it into another store |
| 32 | [Streams-maintained aggregates](32-streams-aggregates/32-streams-aggregates.md) | Running totals from INSERT/MODIFY/REMOVE deltas |
| 33 | [Soft delete & archival](33-soft-delete-archival/33-soft-delete-archival.md) | Soft delete, then TTL, then archive to S3 via the stream |

**Before:** [05-consistency](../05-consistency/README.md) · **Next:** [07-performance-and-scale](../07-performance-and-scale/README.md)
