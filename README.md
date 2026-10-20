# DynamoDB patterns

Industry-standard DynamoDB design patterns as short lessons. Each one has a write-up (`.md`) and a runnable demo (`.py`) that runs against DynamoDB Local.

## Quick start

```sh
direnv allow        # or: nix develop   (provides python 3.13, uv, just)
just setup          # uv sync + pull the DynamoDB Local image
just up             # start DynamoDB Local on localhost:8000
just run 0          # run lesson 00 (the basics)
just run 4          # run pattern 04 (single-table design)
just read 4         # print its write-up
just down           # stop DynamoDB Local
```

| Recipe | What it does |
|---|---|
| `just setup` | Install Python dependencies (`uv sync`) and pull the Docker image |
| `just up` / `just down` | Start / stop DynamoDB Local (data persists in `docker/dynamodb/`) |
| `just reset` | Stop DynamoDB Local and delete its data |
| `just patterns` | List all patterns |
| `just run N` | Run pattern `N` (`4` or `04`) |
| `just read N` | Print pattern `N`'s write-up |
| `just run-all` | Run every pattern and report failures |

Use a different port with `DYNAMODB_PORT=8001 just up` (and the same variable for `just run`). Point the scripts somewhere else entirely with `DYNAMODB_ENDPOINT`.

## How the lessons work

- **Start here:** [`patterns/00-intro/README.md`](patterns/00-intro/README.md) explains what DynamoDB is. Each section folder also has a `README.md` describing what it covers.
- **Layout:** patterns are grouped into category folders: `patterns/<category>/NN-name/NN-name.{md,py}`. Shared helpers live in `patterns/common.py`.
- **Numbering:** the numbers are a reading order. Each pattern only builds on ones before it.
- **Safe to re-run:** each script drops and recreates its own `pNN-*` table.
- **Requests are printed:** every DynamoDB request a script makes is shown (`>>> Query table` with its key condition, filter, condition and update expressions, names and values filled in), so you can see exactly what was sent. Long runs of the same call (e.g. seeding data) are collapsed. Set `LOG_REQUESTS=0` to hide them.
- **Simulated features:** DynamoDB Local doesn't support S3, DAX, PITR/backups, global tables, table export or TTL deletion. Those lessons simulate the behaviour and show the real AWS call in the write-up.

## 0 · [Intro](patterns/00-intro/README.md)
New to DynamoDB? Start with the [overview](patterns/00-intro/README.md): data model, partitions, reads, writes, expressions, indexes, capacity, features and limits.
- [00 · Basics](patterns/00-intro/00-basics/00-basics.md): put, get, update, query, conditional put, delete, scan

## 1 · [Setup](patterns/01-setup/README.md)
- [01 · Local development](patterns/01-setup/01-local-development/01-local-development.md)

## 2 · [Modelling](patterns/02-modelling/README.md)
- [02 · Access-pattern-first design](patterns/02-modelling/02-access-pattern-first/02-access-pattern-first.md)
- [03 · Key prefixes and key overloading](patterns/02-modelling/03-key-prefixes/03-key-prefixes.md)
- [04 · Single-table design](patterns/02-modelling/04-single-table-design/04-single-table-design.md)
- [05 · Composite (hierarchical) sort keys](patterns/02-modelling/05-composite-sort-keys/05-composite-sort-keys.md)
- [06 · Sortable IDs, latest first](patterns/02-modelling/06-sortable-ids-latest-first/06-sortable-ids-latest-first.md)
- [07 · Inverted index](patterns/02-modelling/07-inverted-index/07-inverted-index.md)
- [08 · Adjacency list (many-to-many)](patterns/02-modelling/08-adjacency-list/08-adjacency-list.md)
- [09 · GSI overloading](patterns/02-modelling/09-gsi-overloading/09-gsi-overloading.md)
- [10 · Sparse index](patterns/02-modelling/10-sparse-index/10-sparse-index.md)
- [11 · Denormalization and duplication](patterns/02-modelling/11-denormalization/11-denormalization.md)

## 3 · [Querying](patterns/03-querying/README.md)
- [12 · Avoid Scan (use parallel Scan for batch jobs)](patterns/03-querying/12-avoid-scan-parallel-scan/12-avoid-scan-parallel-scan.md)
- [13 · Filter expressions don't reduce cost](patterns/03-querying/13-filter-expressions-cost/13-filter-expressions-cost.md)
- [14 · Pagination with cursors](patterns/03-querying/14-pagination-cursors/14-pagination-cursors.md)
- [15 · GSI projections](patterns/03-querying/15-gsi-projections/15-gsi-projections.md)
- [16 · Batch operations with retries](patterns/03-querying/16-batch-retries/16-batch-retries.md)

## 4 · [Item size & large data](patterns/04-item-size/README.md)
- [17 · Keep items small (use item collections)](patterns/04-item-size/17-small-items-item-collections/17-small-items-item-collections.md)
- [18 · Vertical partitioning](patterns/04-item-size/18-vertical-partitioning/18-vertical-partitioning.md)
- [19 · Compression](patterns/04-item-size/19-compression/19-compression.md)
- [20 · Offload large items to S3](patterns/04-item-size/20-offload-to-s3/20-offload-to-s3.md)
- [21 · Chunking](patterns/04-item-size/21-chunking/21-chunking.md)

## 5 · [Consistency & concurrency](patterns/05-consistency/README.md)
- [22 · Conditional writes](patterns/05-consistency/22-conditional-writes/22-conditional-writes.md)
- [23 · Optimistic locking](patterns/05-consistency/23-optimistic-locking/23-optimistic-locking.md)
- [24 · Atomic counters](patterns/05-consistency/24-atomic-counters/24-atomic-counters.md)
- [25 · Transactions](patterns/05-consistency/25-transactions/25-transactions.md)
- [26 · Unique constraints on non-key attributes](patterns/05-consistency/26-unique-constraints/26-unique-constraints.md)
- [27 · Idempotency keys](patterns/05-consistency/27-idempotency-keys/27-idempotency-keys.md)
- [28 · GSIs are eventually consistent](patterns/05-consistency/28-gsi-eventual-consistency/28-gsi-eventual-consistency.md)
- [29 · Distributed locking](patterns/05-consistency/29-distributed-locking/29-distributed-locking.md)

## 6 · [Lifecycle & events](patterns/06-lifecycle-and-events/README.md)
- [30 · TTL for expiry](patterns/06-lifecycle-and-events/30-ttl-expiry/30-ttl-expiry.md)
- [31 · DynamoDB Streams / CDC](patterns/06-lifecycle-and-events/31-streams-cdc/31-streams-cdc.md)
- [32 · Streams-maintained aggregates](patterns/06-lifecycle-and-events/32-streams-aggregates/32-streams-aggregates.md)
- [33 · Soft delete & archival](patterns/06-lifecycle-and-events/33-soft-delete-archival/33-soft-delete-archival.md)

## 7 · [Performance & scale](patterns/07-performance-and-scale/README.md)
- [34 · High-cardinality partition keys](patterns/07-performance-and-scale/34-high-cardinality-keys/34-high-cardinality-keys.md)
- [35 · Write sharding](patterns/07-performance-and-scale/35-write-sharding/35-write-sharding.md)
- [36 · Caching (DAX / ElastiCache)](patterns/07-performance-and-scale/36-caching/36-caching.md)
- [37 · Time-series tables](patterns/07-performance-and-scale/37-time-series-tables/37-time-series-tables.md)

## 8 · [Operations](patterns/08-operations/README.md)
- [38 · Capacity modes: on-demand vs provisioned](patterns/08-operations/38-capacity-modes/38-capacity-modes.md)
- [39 · Point-in-time recovery & backups](patterns/08-operations/39-pitr-backups/39-pitr-backups.md)
- [40 · Global tables (multi-region)](patterns/08-operations/40-global-tables/40-global-tables.md)
- [41 · Analytics outside DynamoDB](patterns/08-operations/41-analytics-export/41-analytics-export.md)

## 9 · [What not to do](patterns/09-anti-patterns/README.md)
- [42 · Anti-patterns](patterns/09-anti-patterns/42-anti-patterns/42-anti-patterns.md)
