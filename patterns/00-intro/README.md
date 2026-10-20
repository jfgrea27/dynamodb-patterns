# 00 · Intro: what DynamoDB is

Read this before the patterns. It covers the vocabulary and mechanics that every later lesson assumes. When you're done, run the basics demo: `just run 0` ([00-basics](00-basics/00-basics.md)).

## In one paragraph

Amazon DynamoDB is a fully managed, serverless **key-value and document database**. You create a table and read and write items over an HTTPS API. AWS handles servers, storage, replication, patching and scaling. Its promise is **consistent single-digit-millisecond latency at any scale**, from ten requests a day to millions a second. The price of that promise is that you **design the table around the queries you will run**. DynamoDB is very fast at fetching data by key and deliberately offers nothing slower.

It grew out of Amazon's internal *Dynamo* system ([2007 paper](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)) and launched as an AWS service in 2012.

## The data model

| Term | Meaning |
|---|---|
| **Table** | A collection of items. The only thing you declare up front is the primary key (and any indexes). |
| **Item** | One record, up to **400 KB**. Like a JSON document. |
| **Attribute** | A named value on an item. Items in the same table can have completely different attributes. |
| **Primary key** | Uniquely identifies an item. Either a *partition key* alone, or *partition key + sort key*. |
| **Partition key (PK, "hash key")** | Hashed to decide which physical partition stores the item. |
| **Sort key (SK, "range key")** | Orders items that share a partition key. Enables range queries. |
| **Item collection** | All items that share a partition key value. One `Query` can read all or part of it. |

### Data types

| Type | Code | Example |
|---|---|---|
| String | `S` | `"USER#alice"` |
| Number | `N` | `42`, `3.14`. Sent as a string on the wire, up to 38 digits of precision. |
| Binary | `B` | gzip bytes, images |
| Boolean | `BOOL` | `true` |
| Null | `NULL` | `null` |
| Map | `M` | nested object `{"city": "London"}` |
| List | `L` | `["a", 1, true]` |
| String / Number / Binary set | `SS` / `NS` / `BS` | `{"red", "blue"}`, unique and unordered |

Key attributes must be `S`, `N` or `B`. boto3's resource API (`boto3.resource("dynamodb")`) converts Python values to these types for you. Numbers come back as `Decimal`.

## How data is stored: partitions

```
             hash(PK)
 item ──────────────────▶  partition 1  [ PK=A: SK1, SK2, SK3 ]  [ PK=D: ... ]
                           partition 2  [ PK=B: ... ]
                           partition 3  [ PK=C: ... ]
```

- DynamoDB hashes the partition key to pick a **partition**. Inside a partition, items with the same PK are stored **sorted by SK**.
- A partition holds about **10 GB** and serves up to **3,000 read units/s and 1,000 write units/s**. DynamoDB splits partitions automatically as data or traffic grows.
- Every write is replicated to **three Availability Zones** before it is acknowledged.
- This is why key design matters. Traffic spread across many PK values scales without limit. Traffic concentrated on one PK value (a *hot partition*) hits the per-partition ceiling. See [07-performance-and-scale](../07-performance-and-scale/README.md).

## Reading data

| Operation | What it does | Cost profile |
|---|---|---|
| `GetItem` | Fetch one item by its full primary key | Cheapest, constant time |
| `BatchGetItem` | Up to 100 `GetItem`s in one call (any tables) | Same as the individual gets |
| `Query` | Items from **one** partition key, optionally narrowed by a sort-key condition (`=`, `<`, `>`, `between`, `begins_with`), in SK order, forwards or backwards | Pay only for items read |
| `Scan` | Read every item in the table or index | Pays for the whole table. Batch jobs only. |

- Results come back in **pages of up to 1 MB**. Follow `LastEvaluatedKey` to get the next page.
- **Consistency:** reads are *eventually consistent* by default (half price, may be a moment stale). Pass `ConsistentRead=True` for a *strongly consistent* read on the table (not available on GSIs).
- **Filter expressions** drop items *after* they're read. They save bandwidth, not cost.

## Writing data

| Operation | What it does |
|---|---|
| `PutItem` | Create or **fully replace** an item |
| `UpdateItem` | Change specific attributes (`SET`, `REMOVE`, `ADD`, `DELETE`). Creates the item if it's missing. |
| `DeleteItem` | Remove an item |
| `BatchWriteItem` | Up to 25 puts or deletes in one call. **Not atomic**: some may come back as `UnprocessedItems`. |
| `TransactWriteItems` | Up to 100 actions across tables, **all or nothing** (costs 2× units) |

Any single-item write can carry a **condition expression**, such as "only if it doesn't exist" or "only if `version = 3`". If the condition fails the write is rejected, and nothing changes. Conditions are the foundation of most concurrency patterns in [05-consistency](../05-consistency/README.md).

## Expressions

The request language is a set of small string expressions with placeholders:

```python
table.update_item(
    Key={"PK": "USER#alice", "SK": "PROFILE"},
    UpdateExpression="SET #n = :name ADD loginCount :one",
    ConditionExpression="attribute_exists(PK)",
    ExpressionAttributeNames={"#n": "name"},          # "name" is a reserved word
    ExpressionAttributeValues={":name": "Alice", ":one": 1},
)
```

| Expression | Used for |
|---|---|
| `KeyConditionExpression` | Which partition (and SK range) a `Query` reads |
| `FilterExpression` | Drop items after reading (Query/Scan) |
| `ConditionExpression` | Guard a write |
| `UpdateExpression` | What an `UpdateItem` changes |
| `ProjectionExpression` | Which attributes to return |

boto3's `Key("PK").eq(...)` / `Attr("status").eq(...)` helpers build these for you. The demos in this repo print the final expression for every request.

## Secondary indexes

An index is a second copy of (some of) your data, keyed differently so you can query it another way. DynamoDB keeps it in sync automatically.

| | Global secondary index (GSI) | Local secondary index (LSI) |
|---|---|---|
| Keys | Any partition key + optional sort key | Same partition key, different sort key |
| When created | Any time | Only at table creation |
| Consistency | Eventually consistent only | Strong or eventual |
| Capacity | Its own | Shares the table's |
| Limits | 20 per table (default) | 5 per table. Caps each item collection at 10 GB. |

Prefer GSIs. Items without the index key attributes are left out of the index (a *sparse index*), which turns out to be a powerful tool. Indexes come up throughout [02-modelling](../02-modelling/README.md) and [03-querying](../03-querying/README.md).

## Capacity and cost

You pay for **reads**, **writes** and **storage**:

- **1 read unit** = one strongly consistent read of up to **4 KB** (or two eventually consistent reads). Transactional reads cost 2×.
- **1 write unit** = one write of up to **1 KB**. Transactional writes cost 2×. Every GSI the item lands in costs another write.
- **On-demand mode:** pay per request and scale instantly. **Provisioned mode:** reserve units per second (with auto-scaling). This is cheaper for steady traffic.
- Item size drives cost. A 5 KB item costs 2 read units and 5 write units every time you touch it. This is why [04-item-size](../04-item-size/README.md) exists.

## Built-in features

| Feature | What it gives you | Lesson |
|---|---|---|
| **TTL** | Automatic, free deletion of items after a timestamp | [30](../06-lifecycle-and-events/30-ttl-expiry/30-ttl-expiry.md) |
| **Streams** | An ordered, 24-hour log of every item change, for triggers and replication | [31](../06-lifecycle-and-events/31-streams-cdc/31-streams-cdc.md) |
| **Transactions** | ACID across up to 100 items | [25](../05-consistency/25-transactions/25-transactions.md) |
| **PITR & backups** | Restore to any second in the last 35 days | [39](../08-operations/39-pitr-backups/39-pitr-backups.md) |
| **Global tables** | Multi-region, active-active replication | [40](../08-operations/40-global-tables/40-global-tables.md) |
| **Export to S3** | Full-table export for analytics, without using table capacity | [41](../08-operations/41-analytics-export/41-analytics-export.md) |
| **DAX** | In-memory, microsecond read cache with the same API | [36](../07-performance-and-scale/36-caching/36-caching.md) |
| **PartiQL** | SQL-like syntax (`SELECT * FROM t WHERE PK = ?`). It still only runs efficient key lookups if you write it that way. | n/a |

## Limits worth memorising

| Limit | Value |
|---|---|
| Item size | 400 KB (names + values) |
| Query / Scan page | 1 MB before filtering |
| Per partition | 3,000 RCU/s, 1,000 WCU/s, ~10 GB |
| `BatchWriteItem` / `BatchGetItem` | 25 / 100 items |
| Transaction | 100 items, 4 MB |
| GSIs / LSIs per table | 20 (soft) / 5 |
| LSI item collection | 10 GB |
| Stream retention | 24 hours |
| Nested attribute depth | 32 levels |

## The mental model to carry forward

1. **Start from the access patterns.** Write down every question the app asks, then design keys so each is a `GetItem` or a `Query`.
2. **Store data the way it is read.** Items fetched together share a partition key. Data needed on another item gets copied there.
3. **Spread the load.** Use high-cardinality partition keys so traffic and storage spread across partitions.
4. **Keep items small** and avoid `Scan` in request paths.
5. **Use conditions for correctness.** Atomic updates and conditional writes replace locks.

## Where to go next

| Section | What it covers |
|---|---|
| [01-setup](../01-setup/README.md) | Running DynamoDB Local and keeping tests isolated |
| [02-modelling](../02-modelling/README.md) | Designing keys, single-table design, indexes, relationships |
| [03-querying](../03-querying/README.md) | Reading efficiently: Scan vs Query, filters, pagination, projections, batches |
| [04-item-size](../04-item-size/README.md) | Living with the 400 KB limit and per-KB pricing |
| [05-consistency](../05-consistency/README.md) | Correct concurrent writes: conditions, locking, transactions, idempotency |
| [06-lifecycle-and-events](../06-lifecycle-and-events/README.md) | Expiry, change streams, archival |
| [07-performance-and-scale](../07-performance-and-scale/README.md) | Hot partitions, sharding, caching, time-series |
| [08-operations](../08-operations/README.md) | Capacity, backups, multi-region, analytics |
| [09-anti-patterns](../09-anti-patterns/README.md) | What goes wrong and how to spot it |
