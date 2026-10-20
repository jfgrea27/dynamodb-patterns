# 01 · Setup

How to develop against DynamoDB without an AWS account: run the official emulator locally, make the endpoint configurable, and keep tests isolated from each other.

## Key ideas

- **DynamoDB Local** is AWS's own emulator. It runs in Docker (`just up`) and speaks the same API, so the same boto3 code works locally and in AWS.
- **One switch for the endpoint.** Everything in this repo reads `DYNAMODB_ENDPOINT`. Leave it unset in production and the normal AWS credential chain takes over.
- **Throwaway tables.** Each test, or each lesson here, creates its own table and drops it again, so runs never interfere.
- **Know what's emulated.** Local covers tables, indexes, streams, transactions and PartiQL. It doesn't cover TTL deletion, backups, global tables, throttling or real latency.

## Lessons

| # | Lesson | You'll learn |
|---|---|---|
| 01 | [Local development](01-local-development/01-local-development.md) | Docker setup, endpoint config, fail-fast connection check, per-test tables, Local vs LocalStack vs moto |

**Next:** [02-modelling](../02-modelling/README.md)
