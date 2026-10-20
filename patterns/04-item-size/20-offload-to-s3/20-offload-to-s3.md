# 20 · Offload large items to S3

**Run:** `just run 20`

> DynamoDB Local has no S3, so the script uses a local temp directory as the "bucket". The DynamoDB side is real.

## Problem

A DynamoDB item can be at most **400 KB**, counting attribute names and values. Documents, images, transcripts and large JSON payloads don't fit. Even items that do fit are expensive: every read of a 300 KB item costs about 75 read units (strongly consistent) or about 38 (eventually consistent).

## Pattern

Put the bytes in S3. Keep only small, queryable metadata and a pointer in DynamoDB.

| PK        | SK     | title            | size    | sha256 | s3Bucket       | s3Key          |
|-----------|--------|------------------|---------|--------|----------------|----------------|
| `DOC#d1`  | `META` | Quarterly report | 1048576 | ab12…  | my-docs-bucket | `docs/d1/v1`   |

Write order: **upload to S3 first, then write the DynamoDB item.** If the process crashes in between, you get an orphan object, not a dangling pointer. An S3 lifecycle rule or a sweeper job can clean up orphans.

Real AWS code:

```python
s3 = boto3.client("s3")
s3.put_object(Bucket=BUCKET, Key=key, Body=body)
table.put_item(Item={"PK": f"DOC#{doc_id}", "SK": "META", "s3Key": key, ...})
# read
body = s3.get_object(Bucket=item["s3Bucket"], Key=item["s3Key"])["Body"].read()
```

## Why

- There is no size limit in practice. S3 objects can be up to 5 TB.
- Lists and queries stay cheap because they only read small items.
- S3 storage costs far less per GB than DynamoDB.
- Clients can download directly from S3 using presigned URLs.

## Trade-offs

- Getting the content takes two calls.
- There is no cross-service transaction. You must handle orphans and failures yourself.
- Deletes must remove both sides. A stream handler ([31](../../06-lifecycle-and-events/31-streams-cdc/31-streams-cdc.md)) can delete the S3 object when the item is deleted.

## Gotchas

- Use **versioned or immutable keys** (`docs/d1/v2`). Overwriting the same key lets readers see the new blob with old metadata.
- Store a checksum so readers can detect mismatches.
- If the payload is only somewhat too big, try compression first ([19](../19-compression/19-compression.md)).

Related: [18](../18-vertical-partitioning/18-vertical-partitioning.md), [21](../21-chunking/21-chunking.md), [17](../17-small-items-item-collections/17-small-items-item-collections.md).
