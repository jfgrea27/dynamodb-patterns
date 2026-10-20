# 02 · Modelling

The heart of DynamoDB: deciding **what goes in the partition key, the sort key and the indexes** so that every access pattern is a single `GetItem` or `Query`. Most of the rest of the repo builds on these lessons.

## Key ideas

- **Access patterns come first.** List the questions the app asks, then design keys to answer them. The table shape follows from the queries, not the other way round.
- **Keys are strings you design.** Prefixes (`USER#`, `ORDER#`) and composite values (`COUNTRY#STATE#CITY`) turn one key attribute into a flexible, sortable path.
- **One table, many entities.** Items that are read together share a partition key, so one `Query` returns all of them (an *item collection*).
- **Indexes give you more ways in.** A GSI re-keys the same data. Swapping PK and SK (an inverted index) answers the reverse question. Generic `GSI1PK`/`GSI1SK` attributes let one index serve many patterns. Leaving the key off an item keeps it out of the index entirely (sparse).
- **Duplicate on write to save reads.** Copying a value onto the items that need it is normal, as long as you have a plan to update the copies.

## Lessons

| # | Lesson | You'll learn |
|---|---|---|
| 02 | [Access-pattern-first design](02-access-pattern-first/02-access-pattern-first.md) | Deriving a table and indexes from a list of queries |
| 03 | [Key prefixes and key overloading](03-key-prefixes/03-key-prefixes.md) | `TYPE#id` keys, avoiding collisions, key-builder helpers |
| 04 | [Single-table design](04-single-table-design/04-single-table-design.md) | Several entity types in one table; fetching related data in one query |
| 05 | [Composite sort keys](05-composite-sort-keys/05-composite-sort-keys.md) | Hierarchies with `begins_with`, ranges with `between` |
| 06 | [Sortable IDs, latest first](06-sortable-ids-latest-first/06-sortable-ids-latest-first.md) | ISO-8601 timestamps and ULIDs as sort keys; newest-first queries |
| 07 | [Inverted index](07-inverted-index/07-inverted-index.md) | A GSI with PK/SK swapped to query relationships backwards |
| 08 | [Adjacency list](08-adjacency-list/08-adjacency-list.md) | Many-to-many relationships as edge items |
| 09 | [GSI overloading](09-gsi-overloading/09-gsi-overloading.md) | One generic GSI serving several access patterns |
| 10 | [Sparse index](10-sparse-index/10-sparse-index.md) | Indexes that only contain the items you care about |
| 11 | [Denormalization](11-denormalization/11-denormalization.md) | Copying and embedding data, and keeping copies in sync |

**Before:** [00-intro](../00-intro/README.md) · **Next:** [03-querying](../03-querying/README.md)
