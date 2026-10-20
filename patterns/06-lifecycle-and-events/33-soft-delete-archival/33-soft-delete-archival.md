# 33 · Soft delete & archival

**Run:** `just run 33`

## Problem

Users delete things and then want them back ("trash" / "undo"). Compliance may require you to keep deleted records somewhere. But you don't want deleted items cluttering queries, and you don't want to pay to store them in DynamoDB forever.

## Pattern

Do it in three stages:

1. **Soft delete.** Use `UpdateItem` to set `deletedAt`, set a TTL attribute (`expiresAt`), and `REMOVE` the GSI key attributes. Because GSIs are sparse ([10](../../02-modelling/10-sparse-index/10-sparse-index.md)), the item disappears from list views straight away. It is still readable by key for undo or a trash view.
2. **Hard delete.** When `expiresAt` passes, DynamoDB TTL deletes the item for free ([30](../30-ttl-expiry/30-ttl-expiry.md)).
3. **Archive.** A stream consumer ([31](../31-streams-cdc/31-streams-cdc.md)) sees the `REMOVE` and writes the old image to S3 (cheap, queryable with Athena).

| PK       | SK     | title     | GSI1PK        | deletedAt  | expiresAt  |
|----------|--------|-----------|---------------|------------|------------|
| `DOC#d1` | `META` | Q3 plan   | `FOLDER#work` |            |            |
| `DOC#d2` | `META` | Old draft | *(removed)*   | 1792494255 | +30 days   |

**Undo:** `SET GSI1PK = :folder, GSI1SK = :sk REMOVE deletedAt, expiresAt`.

## Why

- **Undo for free.** Nothing is lost until the retention window ends.
- **Queries stay clean.** No `deletedAt` filter needed on index queries, because the item simply isn't in the index.
- **Cheap long-term storage.** S3 costs a fraction of DynamoDB storage, and TTL deletes consume no write capacity.

## Trade-offs

- Base-table queries on the item collection *will* still return soft-deleted items. Filter on `attribute_not_exists(deletedAt)` there, or move deleted items to a different SK prefix (e.g. `DELETED#META`).
- Unique constraints ([26](../../05-consistency/26-unique-constraints/26-unique-constraints.md)) must decide whether a soft-deleted item still "owns" its unique value.
- The archive is eventually consistent with the table.

## Gotchas

- The stream view type must include the old image (`OLD_IMAGE` or `NEW_AND_OLD_IMAGES`), or you have nothing to archive.
- Tell TTL deletes apart from user deletes with `record["userIdentity"]["principalId"] == "dynamodb.amazonaws.com"` (and `type == "Service"`).
- **Local simulation:** DynamoDB Local accepts `UpdateTimeToLive` but never actually expires items. The script hard-deletes with `DeleteItem` instead, and writes the archive into a dict rather than S3. In AWS the consumer would call `s3.put_object(Bucket="archive", Key=..., Body=json.dumps(old_image))`.
