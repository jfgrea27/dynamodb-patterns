# 02 · Access-pattern-first design

**Run:** `just run 02`

## Problem

In SQL you model entities first and write queries later; the query planner sorts it out. DynamoDB has no planner. If a query isn't backed by a key or index, your only option is a `Scan`.

## Pattern

1. Write down **every** read and write the app needs, with rough frequency.
2. For each one, decide which request serves it: `GetItem`, `Query` on the table, or `Query` on a GSI.
3. Derive `PK`/`SK` and GSI keys from that list. Then check that nothing needs a `Scan`.

| Access pattern                      | Request                                               |
|-------------------------------------|-------------------------------------------------------|
| Get customer                        | `GetItem PK=CUST#<id>, SK=PROFILE`                    |
| Customer's orders, newest first     | `Query PK=CUST#<id>, SK begins_with ORDER#` (desc)    |
| Order by id                         | `Query GSI1 GSI1PK=ORDER#<id>`                        |
| Orders by status for a day          | `Query GSI2 GSI2PK=STATUS#<s>, GSI2SK begins_with <date>` |

Keep this table in your repo. It is the schema.

## Why

- Every request stays a key lookup, so latency is flat at any scale.
- It shows early which GSIs you need, and which ones you don't.

## Trade-offs

- New access patterns later may need a new GSI or a backfill.
- It takes more design work up front than "just add a table".

## Gotchas

- Include write patterns too (e.g. "update order status"). They decide which attributes get duplicated ([11](../11-denormalization/11-denormalization.md)).
- Low-cardinality GSI keys like `STATUS#PENDING` can get hot. Shard them if volume is high ([35](../../07-performance-and-scale/35-write-sharding/35-write-sharding.md)).

Related: [04](../04-single-table-design/04-single-table-design.md), [09](../09-gsi-overloading/09-gsi-overloading.md).
