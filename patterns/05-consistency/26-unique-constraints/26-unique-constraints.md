# 26 · Unique constraints on non-key attributes

**Run:** `just run 26`

## Problem

DynamoDB only enforces uniqueness on the primary key. You want "email must be unique across users", but email isn't the key, and GSIs don't enforce uniqueness.

## Pattern

For each unique value, write a **sentinel item** whose key *is* that value. Write it in the **same transaction** as the main item, with `attribute_not_exists(PK)` on both.

| PK                  | SK        | attributes        |
|---------------------|-----------|-------------------|
| `USER#alice`        | `PROFILE` | email=a@x.com     |
| `EMAIL#a@x.com`     | `EMAIL`   | user_id=alice     |
| `USER#bob`          | `PROFILE` | email=bob@x.com   |
| `EMAIL#bob@x.com`   | `EMAIL`   | user_id=bob       |

- **Create:** `TransactWriteItems[ Put user (not exists), Put EMAIL# sentinel (not exists) ]`
- **Change email:** `TransactWriteItems[ Delete old sentinel, Put new sentinel (not exists), Update user (email = old) ]`
- **Delete user:** delete the user and the sentinel together.

## Why

- Real uniqueness, enforced by DynamoDB, with no race conditions.
- The sentinel is also a free lookup: "which user has this email?" is a `GetItem`.

## Trade-offs

- Transactions cost 2x write capacity and allow at most 100 items.
- Each unique attribute adds one item per entity.
- All writers must use the same transactional path. A plain `PutItem` that skips the sentinel breaks the rule.

## Gotchas

- Normalize the value before using it as a key (lower-case emails, trim spaces). Otherwise `A@x.com` and `a@x.com` are "different".
- On failure, look at `CancellationReasons` to see which item's condition failed (user exists vs. email taken).
- See [25-transactions](../25-transactions/25-transactions.md) and [22-conditional-writes](../22-conditional-writes/22-conditional-writes.md).
