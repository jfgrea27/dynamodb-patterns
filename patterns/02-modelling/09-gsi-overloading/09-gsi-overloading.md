# 09 · GSI overloading

**Run:** `just run 09`

## Problem

Each new access pattern seems to need its own GSI. A table can have at most 20 GSIs, and every GSI adds write cost and storage.

## Pattern

Give GSIs **generic** key names (`GSI1PK`, `GSI1SK`). Each entity type fills them with whatever *it* needs. One index then serves several access patterns.

| Entity   | PK           | GSI1PK                 | GSI1SK           | Serves                         |
|----------|--------------|------------------------|------------------|--------------------------------|
| Employee | `EMP#e1`     | `EMAIL#eve@acme.com`   | `EMP#e1`         | Employee by email              |
| Ticket   | `TICKET#t1`  | `ASSIGNEE#e1`          | `P1#2026-10-18`  | Tickets per assignee, by priority |
| Office   | `OFFICE#o1`  | `CITY#London`          | `OFFICE#o1`      | Offices in a city              |

Prefixes ([03](../03-key-prefixes/03-key-prefixes.md)) keep the values from colliding.

## Why

- Fewer indexes: lower write cost and less to operate.
- New access patterns can often reuse an existing GSI, as long as the new entity type doesn't use it yet.

## Trade-offs

- Index attributes no longer explain themselves. Document what `GSI1PK` means for each type (see [02](../02-access-pattern-first/02-access-pattern-first.md)).
- All entity types share the index's projection ([15](../../03-querying/15-gsi-projections/15-gsi-projections.md)).

## Gotchas

- An item without `GSI1PK` is simply not in the index. That is the sparse-index trick ([10](../10-sparse-index/10-sparse-index.md)).
- When an entity changes (e.g. ticket reassigned), remember to update its GSI attributes too.

Related: [04](../04-single-table-design/04-single-table-design.md), [07](../07-inverted-index/07-inverted-index.md).
