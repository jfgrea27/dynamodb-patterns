# 19 · Compression

**Run:** `just run 19`

## Problem

Items are capped at 400 KB, and you pay per 1 KB written and per 4 KB read. Large text attributes (JSON blobs, transcripts, HTML) push items towards the limit and cost more on every access.

## Pattern

Compress large attributes (gzip, zstd, brotli) in the application and store them as a **Binary** (`B`) attribute. Keep anything you filter on or project as normal, uncompressed attributes.

| PK        | SK           | status    | turns | body_gz            | encoding    |
|-----------|--------------|-----------|-------|--------------------|-------------|
| `CALL#c1` | `TRANSCRIPT` | completed | 200   | `<gzip bytes>`     | `gzip+json` |

## Why

- Text often shrinks 5–20x. That's fewer write units, fewer read units and less storage.
- It keeps a document in a single item when it would otherwise need [21-chunking](../21-chunking/21-chunking.md) or [20-offload-to-s3](../20-offload-to-s3/20-offload-to-s3.md).

## Trade-offs

- DynamoDB can't see inside the blob. You can't filter on it, update part of it, or index it.
- Compression costs CPU on the client.
- The data is opaque in the console and to tools like Athena exports. You must decompress it.

## Gotchas

- Store an `encoding` attribute so you can change the algorithm later.
- Compression helps but doesn't remove the limit. If data can grow without bound, use S3 ([20](../20-offload-to-s3/20-offload-to-s3.md)).
- Binary values are base64-encoded on the wire, but they are billed on their raw byte size.
