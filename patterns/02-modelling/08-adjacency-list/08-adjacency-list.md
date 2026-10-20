# 08 · Adjacency list (many-to-many)

**Run:** `just run 08`

## Problem

Students take many courses and courses have many students. SQL uses a join table. DynamoDB has no joins, and you need to query **both** directions.

## Pattern

Store each node as an item, and each **edge** as its own item. Edge items use one node as `PK` and the other as `SK`. Then add an **inverted GSI** (`PK` = `SK`, `SK` = `PK`) to walk edges backwards.

| PK              | SK              | type      | attrs  |
|-----------------|-----------------|-----------|--------|
| `STUDENT#ann`   | `STUDENT#ann`   | Student   | name   |
| `COURSE#db101`  | `COURSE#db101`  | Course    | title  |
| `STUDENT#ann`   | `COURSE#db101`  | Enrolment | grade  |
| `STUDENT#ben`   | `COURSE#db101`  | Enrolment | grade  |

- **Ann's courses:** `Query PK=STUDENT#ann, SK begins_with COURSE#`
- **Students in db101:** `Query Inverted SK=COURSE#db101, PK begins_with STUDENT#`

## Why

- Both directions take one `Query`.
- Edges can carry attributes (grade, role, joined date).
- It works for graphs too: followers, friends, bill-of-materials.

## Trade-offs

- An edge query returns ids, not full node details. Either duplicate the fields you show on the edge ([11](../11-denormalization/11-denormalization.md)), or do a `BatchGetItem` for the nodes.
- Deleting a node means deleting all its edges too.

## Gotchas

- A very popular node (a celebrity with millions of followers) makes a hot partition on the inverted index. Shard it ([35](../../07-performance-and-scale/35-write-sharding/35-write-sharding.md)).
- Multi-hop graph traversal is still N round trips. For heavy graph work use a graph database.

Related: [07](../07-inverted-index/07-inverted-index.md), [09](../09-gsi-overloading/09-gsi-overloading.md).
