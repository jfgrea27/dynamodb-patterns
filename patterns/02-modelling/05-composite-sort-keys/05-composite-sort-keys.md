# 05 · Composite (hierarchical) sort keys

**Run:** `just run 05`

## Problem

You need to filter at several levels: all stores, stores in a country, in a state, in a city. A key condition can only use the partition key and **one** sort key, and only with `=`, `<`, `>`, `between` or `begins_with`.

## Pattern

Join the levels into one sort key, ordered **most general → most specific**:

| PK           | SK                                  |
|--------------|-------------------------------------|
| `BRAND#acme` | `STORE#US#CA#San Francisco#s1`      |
| `BRAND#acme` | `STORE#US#CA#Los Angeles#s2`        |
| `BRAND#acme` | `STORE#US#NY#New York#s3`           |
| `BRAND#acme` | `STORE#UK#ENG#London#s4`            |

- **Country:** `begins_with(SK, "STORE#US#")`
- **State:** `begins_with(SK, "STORE#US#CA#")`
- **City:** `begins_with(SK, "STORE#UK#ENG#London#")`

The same idea gives range queries when the last part is sortable, e.g. `READING#2026-10-05` `between` `READING#2026-10-31`.

## Why

- One key answers several query shapes, with no extra index.
- Results come back sorted by the hierarchy for free.

## Trade-offs

- You can only filter on a **prefix**. "All stores in any city named London" is not possible without another index.
- Changing the order of the levels means rewriting every item.

## Gotchas

- End each prefix with the delimiter (`US#`, not `US`). Otherwise `US` also matches `USA`.
- Pick a delimiter that never appears in the values, or escape it.
- Sort keys compare as strings (UTF-8 bytes). Zero-pad numbers (`0007`) and use ISO-8601 dates ([06](../06-sortable-ids-latest-first/06-sortable-ids-latest-first.md)).

Related: [03](../03-key-prefixes/03-key-prefixes.md), [04](../04-single-table-design/04-single-table-design.md).
