"""16 - Batch operations with retries: handle UnprocessedItems / UnprocessedKeys with backoff."""

import random
import time

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import client, dynamodb, recreate_table, show

TABLE = "p16-batch-retries"
table = recreate_table(TABLE)

MAX_BATCH_WRITE = 25  # BatchWriteItem limit
MAX_BATCH_GET = 100  # BatchGetItem limit


def chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def flaky_batch_write(RequestItems):
    """DynamoDB Local never throttles. Pretend the first call leaves a third of the items unprocessed."""
    resp = client.batch_write_item(RequestItems=RequestItems)
    if not flaky_batch_write.done:
        flaky_batch_write.done = True
        resp["UnprocessedItems"] = {t: reqs[: len(reqs) // 3] for t, reqs in RequestItems.items()}
        print(f"  (simulated) {sum(map(len, resp['UnprocessedItems'].values()))} items came back unprocessed")
    return resp


flaky_batch_write.done = False


def with_backoff(call, request, unprocessed_key, max_attempts=8):
    """Call a batch API, retrying only what came back unprocessed, with jittered exponential backoff."""
    responses = []
    for attempt in range(max_attempts):
        resp = call(RequestItems=request)
        responses.append(resp)
        request = {t: r for t, r in (resp.get(unprocessed_key) or {}).items() if r}
        if not request:
            return responses
        delay = min(2.0, 0.05 * 2 ** (attempt + 1)) * random.uniform(0.5, 1.0)  # capped, jittered
        print(f"  retry #{attempt + 1} in {delay:.2f}s")
        time.sleep(delay)
    raise RuntimeError(f"still unprocessed after {max_attempts} attempts: {request}")


# --- BatchWriteItem: 60 items -> batches of 25/25/10 ---
items = [{"PK": f"ITEM#{i:03}", "SK": "META", "n": i} for i in range(60)]
show("Writing 60 items in batches of 25")
for batch in chunks(items, MAX_BATCH_WRITE):
    request = {TABLE: [{"PutRequest": {"Item": it}} for it in batch]}
    with_backoff(flaky_batch_write, request, "UnprocessedItems")
    print(f"  wrote batch of {len(batch)}")

# --- BatchGetItem: 60 keys -> 1 batch (limit 100), retrying UnprocessedKeys ---
keys = [{"PK": it["PK"], "SK": it["SK"]} for it in items]
fetched = []
for batch in chunks(keys, MAX_BATCH_GET):
    request = {TABLE: {"Keys": batch, "ProjectionExpression": "PK, n"}}
    for resp in with_backoff(client.batch_get_item, request, "UnprocessedKeys"):
        fetched.extend(resp["Responses"].get(TABLE, []))
show("Fetched back", {"count": len(fetched), "note": "BatchGetItem returns items in no particular order"})

# --- The easy way for writes: batch_writer() chunks to 25 and resends unprocessed items for you ---
with dynamodb.Table(TABLE).batch_writer(overwrite_by_pkeys=["PK", "SK"]) as w:
    for i in range(60, 130):
        w.put_item(Item={"PK": f"ITEM#{i:03}", "SK": "META", "n": i})
show("Items in table after batch_writer() added 70 more", table.scan(Select="COUNT")["Count"])
