# 17 · Keep items small (use item collections)

**Run:** `just run 17`

## Problem

It's tempting to model "a post and its comments" as one item with a `comments` list. That list grows without bound. Reading the title then costs as much as reading every comment, and every append rewrites the whole item.

## Pattern

Keep each item small and bounded. Model "has many" as **separate items in the same partition** (an item collection), not as a list attribute.

| PK        | SK                              | attributes          |
|-----------|---------------------------------|---------------------|
| `POST#p2` | `POST`                          | title, comment_count|
| `POST#p2` | `COMMENT#2026-10-20T10:00`      | by, text            |
| `POST#p2` | `COMMENT#2026-10-20T10:01`      | by, text            |

- **Post only:** `GetItem(PK, SK=POST)`. This is cheap no matter how many comments there are.
- **Latest N comments:** `Query(PK, SK begins_with COMMENT#, ScanIndexForward=False, Limit=N)`

## Why

- **Cost.** Reads are billed per 4 KB and writes per 1 KB of the *whole item*. Updating one field on a 300 KB item costs 300 WCUs.
- **No 400 KB cliff.** Each comment is its own item.
- **Paging.** You can page through comments. You can't page through a list attribute.

## Trade-offs

- Showing a post with all its comments is a `Query`, not a `GetItem`. That's still one request.
- Counts must be kept on the parent (see [24-atomic-counters](../../05-consistency/24-atomic-counters/24-atomic-counters.md) or [32-streams-aggregates](../../06-lifecycle-and-events/32-streams-aggregates/32-streams-aggregates.md)).

## Rule of thumb

A small list that has a hard upper limit (say, 5 tags) is fine as an attribute. Anything unbounded or large should be separate items. Related patterns: [18-vertical-partitioning](../18-vertical-partitioning/18-vertical-partitioning.md), [04-single-table-design](../../02-modelling/04-single-table-design/04-single-table-design.md).

## Gotchas

- Pass `ReturnConsumedCapacity="TOTAL"` to see what a request really costs. The script prints it.
- Hot item collections can still hit the per-partition throughput limit (~1,000 WCU / 3,000 RCU). See [35-write-sharding](../../07-performance-and-scale/35-write-sharding/35-write-sharding.md).
