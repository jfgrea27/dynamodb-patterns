# 14 · Pagination with cursors

**Run:** `just run 14`

## Problem

A Query or Scan returns at most 1 MB (or `Limit` items) per call. DynamoDB has no `OFFSET`, so "page 7" can't be computed. You can only continue from where the last page stopped.

## Pattern

- Each response includes `LastEvaluatedKey` when there's more. Pass it back as `ExclusiveStartKey`.
- For APIs, **encode it as an opaque cursor** (base64 JSON, ideally signed or encrypted) and return it as `nextCursor`.
- No `LastEvaluatedKey` means you've reached the last page.

```python
resp = table.query(KeyConditionExpression=..., Limit=10, ExclusiveStartKey=start)
next_cursor = encode(resp.get("LastEvaluatedKey"))
```

boto3 paginators (`client.get_paginator("query")`) run the loop for you in batch code.

## Why

- **Constant cost per page.** Page 1,000 costs the same as page 1. Offset pagination gets slower the deeper you go.
- **Stable under inserts.** New items don't shift or duplicate the next page.

## Trade-offs

- You can only go forward (you can go backward by reversing `ScanIndexForward` from a cursor), and you can't jump to page N. Use "load more" or infinite scroll UIs.
- **No total count** without reading everything. Keep a separate counter if you need one ([24](../../05-consistency/24-atomic-counters/24-atomic-counters.md)).

## Gotchas

- The cursor contains key values, which may include IDs or emails. **Don't trust it from clients.** Check it belongs to the partition being queried, and consider encrypting it.
- On a GSI, `LastEvaluatedKey` includes both the index keys and the table keys. Pass it back unchanged.
- With a `FilterExpression`, pages can be short or empty while more data remains ([13](../13-filter-expressions-cost/13-filter-expressions-cost.md)).
- Newest-first feeds: sortable keys plus `ScanIndexForward=False` ([06](../../02-modelling/06-sortable-ids-latest-first/06-sortable-ids-latest-first.md)).
