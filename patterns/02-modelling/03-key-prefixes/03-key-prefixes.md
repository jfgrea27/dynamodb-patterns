# 03 · Key prefixes and key overloading

**Run:** `just run 03`

## Problem

In a single table, many entity types share the same `PK`/`SK` attributes. A user with id `42` and an org with id `42` would collide. Raw ids also make it hard to tell what an item is.

## Pattern

Prefix every key value with its entity type and a delimiter:

| PK        | SK               | type       |
|-----------|------------------|------------|
| `USER#42` | `USER#42`        | User       |
| `ORG#42`  | `ORG#42`         | Org        |
| `ORG#42`  | `MEMBER#USER#42` | Membership |
| `ORG#42`  | `PROJECT#p1`     | Project    |

"Key overloading" means the same attribute (`SK`) holds different kinds of values for different items. Prefixes keep that safe, and `begins_with(SK, "MEMBER#")` picks out one kind.

## Why

- No id collisions between entity types.
- Keys are readable in the console and in logs.
- Prefixes give you cheap per-type filtering inside an item collection.

## Trade-offs

- Keys get a bit longer. Key bytes count toward item size and index storage.
- Every caller must build keys the same way. Put key builders in one module.

## Gotchas

- Keep a `type` attribute and the raw id (`userId`) on the item. Don't rely on parsing keys.
- Use a delimiter that can't appear in ids (`#` is the convention).
- Keep prefixes short but clear. They are written millions of times.

Related: [04](../04-single-table-design/04-single-table-design.md), [05](../05-composite-sort-keys/05-composite-sort-keys.md), [09](../09-gsi-overloading/09-gsi-overloading.md).
