# 07 · Inverted index

**Run:** `just run 07`

## Problem

Your base table answers "what's on invoice X?" (`PK=INV#X`). You also need "which invoices contain product Y?" and "which invoices belong to customer Z?". Those values live in the **sort key**, and you can't query by sort key alone.

## Pattern

Create a GSI whose partition key is the table's `SK` and whose sort key is the table's `PK`. That's the whole trick.

| PK (base)  | SK (base)        | Inverted PK      | Inverted SK |
|------------|------------------|------------------|-------------|
| `INV#1001` | `PRODUCT#apple`  | `PRODUCT#apple`  | `INV#1001`  |
| `INV#1002` | `PRODUCT#apple`  | `PRODUCT#apple`  | `INV#1002`  |
| `INV#1001` | `CUSTOMER#c1`    | `CUSTOMER#c1`    | `INV#1001`  |

- **Lines on an invoice:** `Query PK=INV#1001`
- **Invoices with apple:** `Query Inverted SK=PRODUCT#apple`
- **Invoices for c1:** `Query Inverted SK=CUSTOMER#c1`

## Why

- One extra index answers the reverse of **every** relationship in the table.
- It needs no new attributes. It reuses `PK` and `SK`.

## Trade-offs

- Every item is written to the index (it isn't sparse), so it roughly doubles write cost.
- Items whose `SK` is a constant like `PROFILE` or `METADATA` all land in one huge inverted partition. Make sure no access pattern queries those, or use a separate overloaded GSI ([09](../09-gsi-overloading/09-gsi-overloading.md)) instead.

## Gotchas

- GSIs are eventually consistent ([28](../../05-consistency/28-gsi-eventual-consistency/28-gsi-eventual-consistency.md)).
- Popular values (one product on millions of invoices) become hot keys.

Related: [08](../08-adjacency-list/08-adjacency-list.md).
