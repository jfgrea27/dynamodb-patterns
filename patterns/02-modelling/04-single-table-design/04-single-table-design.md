# 04 · Single-table design

**Run:** `just run 04`

## Problem

In a relational database you'd have `users`, `orders` and `addresses` tables and JOIN them. DynamoDB has no joins. One table per entity means several round trips to show a single page.

## Pattern

Put every entity type in **one table** with generic key names (`PK`, `SK`). Items that are read together share a partition key. Together they form an **item collection**, and one `Query` fetches all of them.

| PK           | SK                    | type    | attributes           |
|--------------|-----------------------|---------|----------------------|
| `USER#alice` | `PROFILE`             | User    | name, email          |
| `USER#alice` | `ADDRESS#home`        | Address | city                 |
| `USER#alice` | `ORDER#2026-10-01#o1` | Order   | total                |
| `USER#alice` | `ORDER#2026-10-15#o2` | Order   | total                |
| `USER#bob`   | `PROFILE`             | User    | name, email          |

Access patterns served:

- **Get profile:** `GetItem(PK=USER#alice, SK=PROFILE)`
- **Everything for a user:** `Query(PK=USER#alice)`
- **User's orders, newest first:** `Query(PK=USER#alice, SK begins_with ORDER#, ScanIndexForward=False)`

## Why

- **Fewer requests.** Related data is pre-joined at write time.
- **One table to operate.** Capacity, alarms, backups, streams and IAM all live in one place.
- **It scales.** Every access pattern is a key lookup, so latency stays flat at any size.

## Trade-offs

- You must know your access patterns up front (see [02](../02-access-pattern-first/02-access-pattern-first.md)). Ad-hoc queries are hard.
- Items are harder to read in the console. Use a `type` attribute and readable prefixes.
- Schema changes often need a backfill (re-write items with new keys or GSI attributes).
- Multiple tables are still fine when entities are never read together, or when they have very different operational needs (e.g. TTL, streams, throughput). Single-table design is a tool, not a religion.

## Gotchas

- Store the entity's real ID as a normal attribute too (`userId`), not only inside `PK`. Parsing keys is brittle.
- An item collection has no size limit on a table with no LSIs. With an LSI it is capped at 10 GB.

## Further reading

- Alex DeBrie, *The DynamoDB Book*
- AWS re:Invent, "Advanced design patterns for DynamoDB" (Rick Houlihan)
