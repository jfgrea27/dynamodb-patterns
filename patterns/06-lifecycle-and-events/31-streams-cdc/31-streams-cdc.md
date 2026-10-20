# 31 · DynamoDB Streams / CDC

**Run:** `just run 31`

## Problem

When an item changes, other systems often need to know: a search index, a cache, an analytics pipeline, another service. If the app writes to DynamoDB *and* calls those systems, a crash between the two calls leaves them out of sync (the "dual write" problem).

## Pattern

Turn on **DynamoDB Streams**. Every insert, update and delete is written to an ordered, durable change log for 24 hours. A consumer (usually a Lambda) reads the log and pushes changes downstream. The table write becomes the single source of truth. The stream acts as a built-in **transactional outbox**.

| Stream view type     | Record contains                  | Use for                         |
|----------------------|----------------------------------|---------------------------------|
| `KEYS_ONLY`          | keys only                        | "something changed, re-read it" |
| `NEW_IMAGE`          | item after the change            | search sync, replication        |
| `OLD_IMAGE`          | item before the change           | auditing deletes                |
| `NEW_AND_OLD_IMAGES` | both                             | diffs, aggregates ([32](../32-streams-aggregates/32-streams-aggregates.md)) |

The script writes, updates and deletes an order, then replays the stream into a dict that stands in for a search index.

In AWS you don't poll by hand. You attach a Lambda:

```python
lambda_client.create_event_source_mapping(
    EventSourceArn=table.latest_stream_arn,
    FunctionName="sync-to-search",
    StartingPosition="LATEST",
    BatchSize=100,
    BisectBatchOnFunctionError=True,
    DestinationConfig={"OnFailure": {"Destination": dlq_arn}},
)
```

## Why

- **No dual writes.** If the table write succeeds, the change event will exist.
- **Changes arrive in order per item.** Records for one key are ordered within a shard.
- **Decoupled.** Add new consumers later without touching the writer.

## Trade-offs

- **At-least-once delivery.** Consumers must be idempotent ([27](../../05-consistency/27-idempotency-keys/27-idempotency-keys.md)).
- **24-hour retention.** If a consumer is broken for longer than that, events are lost. Use Kinesis Data Streams for DynamoDB if you need longer retention or more than 2 consumers.
- **Eventually consistent downstream.** Readers of the search index see changes a little later.
- A shard supports about 2 concurrent readers. Fan out through EventBridge or SNS if more systems need the events.

## Gotchas

- A failing record blocks its shard and retries until it expires. Always set `BisectBatchOnFunctionError`, a max retry count and an on-failure destination.
- TTL deletes appear on the stream with `userIdentity.principalId = "dynamodb.amazonaws.com"`. Use that to tell expiry apart from user deletes ([30](../30-ttl-expiry/30-ttl-expiry.md), [33](../33-soft-delete-archival/33-soft-delete-archival.md)).
- DynamoDB Local supports Streams, so this script runs locally as-is.
