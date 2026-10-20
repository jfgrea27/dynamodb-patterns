# 42 · Anti-patterns

**Run:** `just run 42`

Most DynamoDB pain comes from a short list of mistakes. The script measures each one with `ReturnConsumedCapacity` and request counts. Numbers below come from a run against DynamoDB Local.

## 1. Relational modeling (one table per entity, joins in code)

**Smell:** `users`, `orders` and `addresses` tables, with the app fetching a user and then looping over order IDs.
**Cost:** N+1 requests. Loading a user with 3 orders took **4 requests vs 1**, and latency grows with N.
**Fix:** put items that are read together in one item collection ([04](../../02-modelling/04-single-table-design/04-single-table-design.md), [11](../../02-modelling/11-denormalization/11-denormalization.md)). Design from access patterns ([02](../../02-modelling/02-access-pattern-first/02-access-pattern-first.md)).

## 2. Unbounded lists or maps inside one item

**Smell:** `comments: [...]`, `events: [...]` or `followers: {...}` that grow forever.
**Cost:** every update rewrites the **whole** item. Appending 10 KB messages cost 10 WCU at first and **392 WCU** by the 40th append, which then failed with *"Item size to update has exceeded the maximum allowed size"* (400 KB).
**Fix:** one item per child (`PK=CHAT#c1, SK=MSG#<ulid>`) and query the collection ([17](../../04-item-size/17-small-items-item-collections/17-small-items-item-collections.md), [06](../../02-modelling/06-sortable-ids-latest-first/06-sortable-ids-latest-first.md)). For big blobs, see [20](../../04-item-size/20-offload-to-s3/20-offload-to-s3.md)–[21](../../04-item-size/21-chunking/21-chunking.md).

## 3. Low-cardinality partition key

**Smell:** `PK = status`, `PK = date`, `PK = tenant` when one tenant is huge, or `PK = "ALL"`.
**Cost:** traffic piles onto a few keys. With 90% of orders `PENDING`, 90% of the load hits one partition key, which is capped at about 1,000 WCU / 3,000 RCU per second. Throttling follows, however much capacity the table has.
**Fix:** a high-cardinality PK (e.g. `ORDER#id`) ([34](../../07-performance-and-scale/34-high-cardinality-keys/34-high-cardinality-keys.md)). Serve "by status" from a sparse GSI ([10](../../02-modelling/10-sparse-index/10-sparse-index.md)), and shard keys that are hot by nature ([35](../../07-performance-and-scale/35-write-sharding/35-write-sharding.md)).

## 4. Scan + FilterExpression instead of a key query

**Smell:** `table.scan(FilterExpression=Attr("customer").eq(x))` on a request path.
**Cost:** you pay for every item **read**, not every item returned. Finding one customer's 10 orders out of 1,000 cost **68 RCU via Scan vs 1 RCU via a GSI Query**, and the scan gets worse as the table grows.
**Fix:** add a key or GSI for the access pattern ([09](../../02-modelling/09-gsi-overloading/09-gsi-overloading.md), [07](../../02-modelling/07-inverted-index/07-inverted-index.md)). See [12](../../03-querying/12-avoid-scan-parallel-scan/12-avoid-scan-parallel-scan.md) and [13](../../03-querying/13-filter-expressions-cost/13-filter-expressions-cost.md).

## 5. Too many GSIs

**Smell:** one GSI per attribute "just in case", up to the limit of 20.
**Cost:** every write is repeated into each index that projects the item. A ~1 KB put cost **1 WCU with 0 GSIs, 3 with 2, 6 with 5**. An under-provisioned GSI also throttles writes to the base table.
**Fix:** overload a few generic GSIs (`GSI1PK/GSI1SK`) to serve many patterns ([09](../../02-modelling/09-gsi-overloading/09-gsi-overloading.md)), keep them sparse ([10](../../02-modelling/10-sparse-index/10-sparse-index.md)), and project only what you need ([15](../../03-querying/15-gsi-projections/15-gsi-projections.md)).

## 6. Ad-hoc analytics on the live table

**Smell:** reporting queries, dashboards or "export everything" jobs scanning production tables.
**Cost:** full scans every time (see #4) that compete with user traffic for capacity. There is still no GROUP BY, JOIN or ORDER BY on non-key attributes.
**Fix:** export to S3 + Athena, zero-ETL to Redshift or OpenSearch, or stream to a lake ([41](../../08-operations/41-analytics-export/41-analytics-export.md), [31](../../06-lifecycle-and-events/31-streams-cdc/31-streams-cdc.md)).

## Also watch for

- **Not handling `UnprocessedItems`** in batch calls, which silently loses writes ([16](../../03-querying/16-batch-retries/16-batch-retries.md)).
- **Reading GSIs right after writing** and expecting to see the write ([28](../../05-consistency/28-gsi-eventual-consistency/28-gsi-eventual-consistency.md)).
- **Offset pagination** ("page 7"). DynamoDB only has cursors ([14](../../03-querying/14-pagination-cursors/14-pagination-cursors.md)).
- **Read-modify-write without conditions**, which causes lost updates ([23](../../05-consistency/23-optimistic-locking/23-optimistic-locking.md), [22](../../05-consistency/22-conditional-writes/22-conditional-writes.md)).
- **Random UUIDs as sort keys** when you need time order ([06](../../02-modelling/06-sortable-ids-latest-first/06-sortable-ids-latest-first.md)).
