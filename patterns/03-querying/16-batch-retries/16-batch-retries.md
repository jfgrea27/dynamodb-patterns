# 16 · Batch operations with retries

**Run:** `just run 16`

## Problem

`BatchWriteItem` and `BatchGetItem` save round trips, but they can **partly succeed**. If some items are throttled or the response is too big, the call still returns HTTP 200 and lists the leftovers in `UnprocessedItems` / `UnprocessedKeys`. Code that ignores them silently loses writes or misses reads.

## Pattern

1. **Chunk** to the API limits: 25 puts/deletes per `BatchWriteItem` (16 MB max), 100 keys per `BatchGetItem` (16 MB max).
2. After every call, **resend only the unprocessed part**.
3. Wait between retries with **exponential backoff + jitter**, and give up after N attempts.

```python
for attempt in range(max_attempts):
    resp = client.batch_write_item(RequestItems=request)
    request = resp["UnprocessedItems"]
    if not request:
        break
    time.sleep(min(cap, base * 2**attempt) * random.uniform(0.5, 1))
```

For writes, boto3's `Table.batch_writer()` already chunks to 25 and resends unprocessed items. `overwrite_by_pkeys` drops duplicate keys within a batch, which would otherwise fail validation. There is no equivalent helper for `BatchGetItem`, so write the loop yourself.

DynamoDB Local never throttles, so the script fakes one partial failure to show the retry path.

## Why

- **Fewer round trips.** One request instead of 25 or 100.
- **Correctness.** The retry loop is what makes batches safe to use.
- Jittered backoff stops many clients retrying in lockstep and making throttling worse.

## Trade-offs

- **Not atomic.** Some items can succeed while others fail. Use `TransactWriteItems` when it must be all-or-nothing ([25](../../05-consistency/25-transactions/25-transactions.md)).
- **Costs the same capacity** as single calls. Batching saves latency, not money.
- No conditions or updates in `BatchWriteItem`: only `PutRequest` (full overwrite) and `DeleteRequest`.

## Gotchas

- The same key twice in one batch raises `ValidationException`.
- `BatchGetItem` returns items **in any order**. Match them up by key.
- Unprocessed items usually point to a hot partition or under-provisioned capacity ([35](../../07-performance-and-scale/35-write-sharding/35-write-sharding.md), [38](../../08-operations/38-capacity-modes/38-capacity-modes.md)). Retrying hides the symptom, so alarm on throttling metrics too.
- The AWS SDKs also retry *throttling errors* themselves (`retries={"mode": "adaptive"}` in botocore `Config`). That is separate from `Unprocessed*`, which you must always handle.
