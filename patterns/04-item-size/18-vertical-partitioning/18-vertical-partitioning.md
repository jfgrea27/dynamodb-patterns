# 18 · Vertical partitioning

**Run:** `just run 18`

## Problem

One logical entity has grown into a fat item: summary fields, a long description, specs, reviews, stock. Two things go wrong:

- **Reads are expensive.** A listing page that needs only name and price still pays for the whole item. Reads are billed per 4 KB.
- **Writes are expensive.** Updating one counter (`stock`) is billed on the **full item size**. Writes are billed per 1 KB of the item.

It also creeps toward the 400 KB limit.

## Pattern

Split the entity into several items under the **same partition key**, grouped by how they're accessed:

| PK           | SK           | attributes            | Access                   |
|--------------|--------------|-----------------------|--------------------------|
| `PRODUCT#p2` | `SUMMARY`    | name, price           | listing pages (hot)      |
| `PRODUCT#p2` | `INVENTORY`  | stock                 | changes often            |
| `PRODUCT#p2` | `DETAILS`    | description, specs    | product page only        |
| `PRODUCT#p2` | `REVIEW#u1`  | user, text            | paged, unbounded         |

- **Listing:** `GetItem SK=SUMMARY`. Small and cheap.
- **Stock change:** `UpdateItem SK=INVENTORY`. Billed on a tiny item.
- **Product page:** `Query PK=PRODUCT#p2`, which returns the parts in one request. Or use `BatchGetItem` for exactly the parts you need.

The script prints consumed capacity for both designs. On a ~52 KB product it shows 6.5 vs 0.5 read units for the listing read, and **52 vs 1** write units for a stock change.

## Why

- You pay only for the bytes each access pattern needs.
- Hot, frequently-updated fields don't rewrite cold, large ones.
- Unbounded parts (reviews) become separate items and can't hit the 400 KB limit.

## Trade-offs

- Reading the whole entity takes a `Query` (or several gets) instead of one `GetItem`.
- Changes that span parts need a transaction ([25](../../05-consistency/25-transactions/25-transactions.md)) to stay atomic.
- The app must put the parts back together.

## Gotchas

- Choose sort keys so useful groups are contiguous. A `begins_with` or range query can then fetch "summary + details" without the reviews.
- Don't over-split. Fields that are always read and written together belong on the same item.
- If one part is still too big, move it to S3 ([20](../20-offload-to-s3/20-offload-to-s3.md)) or compress it ([19](../19-compression/19-compression.md)).

Related: [17](../17-small-items-item-collections/17-small-items-item-collections.md), [04](../../02-modelling/04-single-table-design/04-single-table-design.md).
