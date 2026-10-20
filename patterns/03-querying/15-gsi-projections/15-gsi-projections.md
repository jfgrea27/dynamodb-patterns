# 15 · GSI projections

**Run:** `just run 15`

## Problem

A GSI is a separate copy of your data. The projection decides which attributes are copied. Copying too much costs storage, plus write capacity on every update. Copying too little forces an extra read for each result.

## Pattern

Choose the projection per index, based on what the access pattern needs to return:

| Projection  | Copies                      | Use when                                                   |
|-------------|-----------------------------|------------------------------------------------------------|
| `KEYS_ONLY` | table + index keys          | You only need IDs, or you'll `BatchGetItem` a few results. |
| `INCLUDE`   | keys + named attributes     | List views needing a few fields (customer, total).         |
| `ALL`       | everything                  | The index serves full-item reads, or items are small.      |

The script builds all three on the same data and shows what each returns. `KEYS_ONLY` needs a follow-up `BatchGetItem` to get the other fields.

## Why

- **Write cost.** A table write also writes to each GSI whose projected attributes changed. With `ALL`, updating a large blob that no index queries is still copied to the index.
- **Storage.** Large, rarely needed attributes (`lineItems`, descriptions) shouldn't be copied into every index.

## Trade-offs

- **You can't change a GSI's projection.** You must create a new index and drop the old one. If unsure, `ALL` is the safe default for small items.
- `KEYS_ONLY` plus a fetch costs an extra round trip and extra RCUs per result.

## Gotchas

- Querying a GSI for an attribute that isn't projected returns the item **without** that attribute. There's no error, so it's easy to miss.
- Sparse indexes ([10](../../02-modelling/10-sparse-index/10-sparse-index.md)) and overloaded GSIs ([09](../../02-modelling/09-gsi-overloading/09-gsi-overloading.md)) multiply these savings.
- DynamoDB Local reports the same `IndexSizeBytes` for every index. On AWS, look at `IndexSizeBytes` in `DescribeTable` (updated about every 6 hours).
