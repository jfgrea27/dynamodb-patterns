# 30 · TTL for expiry

**Run:** `just run 30`

## Problem

Sessions, OTP codes, idempotency records, locks, caches and old events all need deleting eventually. A cron job that scans and deletes them costs capacity and is one more thing to run.

## Pattern

Enable **Time To Live** on a Number attribute holding an **epoch time in seconds**. DynamoDB deletes items after that time, in the background, for free.

```python
client.update_time_to_live(
    TableName="...",
    TimeToLiveSpecification={"Enabled": True, "AttributeName": "expiresAt"},
)
table.put_item(Item={"PK": "USER#alice", "SK": "SESSION#abc", "expiresAt": int(time.time()) + 3600})
```

| PK           | SK            | expiresAt    | result            |
|--------------|---------------|--------------|-------------------|
| `USER#alice` | `SESSION#old` | now − 60     | eligible to delete|
| `USER#alice` | `SESSION#new` | now + 3600   | kept              |
| `USER#alice` | `PROFILE`     | (missing)    | never expires     |

## Why

- **Free deletes.** TTL deletes use no write capacity.
- No sweeper jobs to run.
- TTL deletes appear in **Streams** (`userIdentity.principalId = dynamodb.amazonaws.com`), so you can archive expired items to S3 ([31](../31-streams-cdc/31-streams-cdc.md), [33](../33-soft-delete-archival/33-soft-delete-archival.md)).

## Trade-offs

- **Not precise.** Deletion usually happens within a few days of expiry. Expired items stay readable until then.
- One TTL attribute per table. Items without it never expire.

## Gotchas

- **Always filter expired items on read:** `attribute_not_exists(expiresAt) OR expiresAt > :now`.
- **Seconds, not milliseconds.** A millisecond value looks like a date tens of thousands of years away, so the item is never deleted. The script shows this bug.
- Items expired more than 5 years ago are ignored. The value must be a Number, not a String.
- Turning TTL on or off can take up to an hour on AWS.
- DynamoDB Local accepts `UpdateTimeToLive`, but don't rely on it to delete items on the AWS schedule. Test the read-side filter instead.
