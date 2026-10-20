# 06 · Sortable IDs, latest first

**Run:** `just run 06`

## Problem

Feeds, chat messages, audit logs and orders are almost always read newest first, or by time range. Sort keys are compared as strings (byte order). Random IDs (UUIDv4) and unpadded numbers don't sort by time.

## Pattern

Make the sort key **sort lexicographically by time**:

| Option            | SK example                                      | Notes                               |
|-------------------|-------------------------------------------------|-------------------------------------|
| ISO-8601 + suffix | `MSG#2026-10-04T00:00:00.000+00:00#e15102`      | Human-readable. Suffix keeps keys unique. |
| ULID              | `MSG#01M423BP00MRKZ02TD5VJE5ZWK`                | 26 chars, unique, time-ordered.     |
| KSUID / UUIDv7    | `MSG#018f3c...`                                 | Same idea, other formats.           |

Then:

- **Latest N:** `Query(PK=ROOM#x, ScanIndexForward=False, Limit=N)`
- **Time range:** `Key("SK").between("MSG#2026-10-02", "MSG#2026-10-05~")`

## Why

- Newest-first and time-range queries become a single cheap Query. Nothing is sorted in code.
- ULIDs give you the ID and the timestamp in one value, and no two collide.

## Trade-offs

- A time-ordered sort key is fine. A time-ordered **partition key** (e.g. `PK=DATE#2026-10-20`) is a hot partition. Shard or bucket it ([35](../../07-performance-and-scale/35-write-sharding/35-write-sharding.md), [37](../../07-performance-and-scale/37-time-series-tables/37-time-series-tables.md)).
- ULIDs aren't human-readable. Store a readable `createdAt` too.

## Gotchas

- Always use **UTC** and a fixed format. Mixing `+00:00` and `Z`, or different precisions, breaks the ordering.
- Zero-pad numbers (`ORDER#0042`, not `ORDER#42`), or `10` sorts before `9`.
- Use `~` (which sorts after alphanumerics) as an inclusive upper bound for a prefix range.
- In real code, use the `python-ulid` package rather than the small helper in the script.
