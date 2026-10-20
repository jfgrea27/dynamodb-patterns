# 00 · Basics

**Run:** `just run 00`

## Problem

Before the patterns make sense you need the everyday API: how to write an item, read it back, change it, query a partition and delete it.

## Pattern

One table with a composite key (`PK` partition key, `SK` sort key) holding animals:

| PK           | SK      | attributes                        |
|--------------|---------|-----------------------------------|
| `ANIMAL#dog` | `Bella` | age                               |
| `ANIMAL#dog` | `Rex`   | age, breed, tags (string set)     |
| `ANIMAL#cat` | `Tom`   | age, owner (map)                  |

The script walks through each core operation:

| Operation | Call | Notes |
|---|---|---|
| Create / replace | `put_item(Item=...)` | Replaces the whole item if the key exists |
| Read one | `get_item(Key=...)` | Needs the full key. Missing items return no `Item`, not an error. |
| Change some attributes | `update_item(UpdateExpression="SET ... REMOVE ...")` | `ReturnValues="ALL_NEW"` returns the result |
| Read a partition | `query(KeyConditionExpression=Key("PK").eq(...))` | Sorted by SK. `ScanIndexForward=False` reverses. |
| Narrow by sort key | `& Key("SK").begins_with("R")` | Also `between`, `<`, `>`, `=` |
| Guarded write | `ConditionExpression="attribute_not_exists(PK)"` | Raises `ConditionalCheckFailedException` |
| Delete | `delete_item(Key=..., ReturnValues="ALL_OLD")` | Returns the deleted item |
| Read everything | `scan()` | Reads the whole table. Avoid outside batch jobs. |

## Why

Every pattern in this repo is a combination of these calls with carefully chosen keys. Watch the printed `>>>` requests to see the expressions boto3 actually sends.

## Gotchas

- `put_item` **replaces** the whole item. Use `update_item` to change some attributes.
- Numbers come back as `Decimal`, and sets come back as Python `set`.
- Words like `name`, `status` and `date` are reserved in expressions. Use `ExpressionAttributeNames` (`#n`) to refer to them.
- Next: read the overview in [00-intro/README.md](../README.md) if you haven't, then start with [02 · Access-pattern-first design](../../02-modelling/02-access-pattern-first/02-access-pattern-first.md).
