# 21 · Chunking

**Run:** `just run 21`

## Problem

A value is bigger than the 400 KB item limit, even after [19-compression](../19-compression/19-compression.md), and you can't or won't use S3.

## Pattern

Split the value into fixed-size pieces. Store each piece as its own item under the same partition key, with a zero-padded sort key. A manifest item records how many chunks there are.

| PK               | SK           | attributes             |
|------------------|--------------|------------------------|
| `DOC#report-2026`| `CHUNK#0000` | data (300 KB), version |
| `DOC#report-2026`| `CHUNK#0001` | data (300 KB), version |
| `DOC#report-2026`| `CHUNK#0002` | data, version          |
| `DOC#report-2026`| `MANIFEST`   | chunks=4, size, version|

Read with `Query(PK=DOC#..., SK begins_with CHUNK#)` and concatenate the pieces in order.

## Why

- No extra service is needed. Everything stays in DynamoDB, including backups, streams and IAM.
- Reads stay in one partition and are ordered by the sort key.

## Trade-offs

- **This is usually the wrong choice.** [20-offload-to-s3](../20-offload-to-s3/20-offload-to-s3.md) is cheaper and simpler for large blobs. DynamoDB storage and throughput cost much more per GB than S3.
- Reading 1 MB costs about 250 RCUs (strongly consistent). S3 GET is a flat fee.
- Writes aren't atomic unless you use a transaction (max 100 items, 4 MB total; see [25-transactions](../../05-consistency/25-transactions/25-transactions.md)). Readers can see a half-written document.

## Gotchas

- Zero-pad chunk numbers (`0001`, not `1`). Otherwise `CHUNK#10` sorts before `CHUNK#2`.
- Put a `version` on every chunk and on the manifest. Readers should reject a mix of versions. Writers should write new chunks first, then flip the manifest.
- `Query` returns at most 1 MB per page. Always follow `LastEvaluatedKey`.
- When a document shrinks, delete the extra chunks left over from the old version.
