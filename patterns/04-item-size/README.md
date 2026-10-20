# 04 · Item size & large data

An item can be at most **400 KB**, and you pay per 4 KB read and per 1 KB written, every time. Item size is therefore both a hard limit and a cost lever. This section covers keeping items small and what to do when data is genuinely big.

## Key ideas

- **Small items are cheap items.** A 40 KB item costs 40 write units for a one-byte change. Unbounded lists inside an item grow the cost on every append until they hit the limit.
- **Split by access pattern (vertical partitioning).** Data that's read or written separately (summary vs details vs reviews) becomes separate items under the same partition key.
- **Compress what you can't split.** Large text or JSON attributes gzip well and fit in a Binary attribute.
- **Big blobs belong in S3.** Store the object in S3 and keep a pointer and metadata in DynamoDB. Chunking across items works but is rarely the better choice.

## Lessons

| # | Lesson | You'll learn |
|---|---|---|
| 17 | [Keep items small (item collections)](17-small-items-item-collections/17-small-items-item-collections.md) | One item per child instead of a growing list; measured read costs |
| 18 | [Vertical partitioning](18-vertical-partitioning/18-vertical-partitioning.md) | Splitting a fat entity into SUMMARY / DETAILS / ... items |
| 19 | [Compression](19-compression/19-compression.md) | Gzipping a large attribute into Binary |
| 20 | [Offload large items to S3](20-offload-to-s3/20-offload-to-s3.md) | Pointer + metadata + checksum in DynamoDB, the object in S3 |
| 21 | [Chunking](21-chunking/21-chunking.md) | Splitting a blob across items with a manifest, and why S3 usually wins |

**Before:** [03-querying](../03-querying/README.md) · **Next:** [05-consistency](../05-consistency/README.md)
