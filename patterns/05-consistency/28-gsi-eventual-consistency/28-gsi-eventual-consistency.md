# 28 · GSIs are eventually consistent

**Run:** `just run 28`

## Problem

GSIs are updated **asynchronously** after the table write succeeds. A read straight after a write can miss the new item or return the old version. `ConsistentRead=True` is rejected on a GSI.

## Pattern

Design so this doesn't matter, or work around it:

1. **Read your own writes from the base table.** After a write, `GetItem`/`Query` the table by primary key with `ConsistentRead=True`.
2. **Return what you wrote.** The API response uses the item you just wrote, not a re-query of the index.
3. **Short retry with backoff** when you must read from the index (see `query_gsi_until_found` in the script).
4. **Never rely on a GSI for invariants.** It doesn't enforce uniqueness, and it can lag. Use conditional writes or transactions on the base table ([22](../22-conditional-writes/22-conditional-writes.md), [26](../26-unique-constraints/26-unique-constraints.md)).

## Why

- Replication to an index usually takes well under a second, but there's no upper bound. During throttling or heavy writes it can be longer.
- "Check the GSI then write" races. Two users can register the same email if you check uniqueness via a GSI.

## Trade-offs

- Base-table consistent reads cost twice as much as eventually consistent ones.
- LSIs **do** support strong consistency, but must be created with the table, cap each item collection at 10 GB, and share the partition's throughput.

## Gotchas

- **Back-pressure.** If a GSI is under-provisioned, it throttles **writes to the base table**. Provision GSIs at least as high as the table, or use on-demand ([38](../../08-operations/38-capacity-modes/38-capacity-modes.md)).
- DynamoDB Local updates indexes instantly, so it won't reproduce this. Test the logic, not the timing.
