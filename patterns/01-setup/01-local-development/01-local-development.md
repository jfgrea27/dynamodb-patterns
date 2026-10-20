# 01 · Local development

**Run:** `just run 01` (needs `just up`)

## Problem

Developing straight against AWS is slow, costs money, needs credentials, and lets tests collide in shared tables. Mocking boto3 by hand misses real behaviour like condition failures, key validation and GSI queries.

## Pattern

Run **DynamoDB Local** (AWS's official emulator) in Docker, and make the endpoint configurable.

```yaml
# docker-compose.yml (this repo)
services:
  dynamodb-local:
    image: amazon/dynamodb-local:latest
    command: "-jar DynamoDBLocal.jar -sharedDb -dbPath ./data"
    ports: ["8000:8000"]
    volumes: ["./docker/dynamodb:/home/dynamodblocal/data"]
```

```python
endpoint = os.environ.get("DYNAMODB_ENDPOINT")  # unset in prod
boto3.resource("dynamodb", endpoint_url=endpoint, ...)
```

For tests, give **each test its own uniquely named table** and always delete it (the script's `temp_table()` context manager, or a pytest fixture). Build tables from the same definition as prod, ideally exported from your IaC (CDK, Terraform, CloudFormation).

| Tool                 | Good for                                     | Notes                                   |
|----------------------|----------------------------------------------|-----------------------------------------|
| **DynamoDB Local**   | realistic API behaviour, streams, PartiQL, transactions | official; Java/Docker              |
| **LocalStack**       | DynamoDB *plus* S3, Lambda, SQS, etc.        | wraps DynamoDB Local for DynamoDB       |
| **moto**             | fast in-process unit tests, no Docker        | `@mock_aws`; less faithful               |

## Why

- **Fast and free.** No network round trip to AWS, no bill.
- **Realistic.** Catches condition, key and index mistakes that hand-written mocks don't.
- **Isolated.** Unique tables per test mean parallel test runs don't interfere.

## Trade-offs

What DynamoDB Local **doesn't** do (patterns that need these are simulated in this folder):

- No throttling or capacity limits, so performance looks better than reality ([38](../../08-operations/38-capacity-modes/38-capacity-modes.md), [16](../../03-querying/16-batch-retries/16-batch-retries.md)).
- TTL never actually deletes items ([30](../../06-lifecycle-and-events/30-ttl-expiry/30-ttl-expiry.md)).
- No PITR or backups ([39](../../08-operations/39-pitr-backups/39-pitr-backups.md)), global tables ([40](../../08-operations/40-global-tables/40-global-tables.md)), exports ([41](../../08-operations/41-analytics-export/41-analytics-export.md)), or DAX ([36](../../07-performance-and-scale/36-caching/36-caching.md)).
- GSIs update immediately, so eventual-consistency bugs don't show up ([28](../../05-consistency/28-gsi-eventual-consistency/28-gsi-eventual-consistency.md)).

Keep a small integration suite that runs against a real AWS account in CI.

## Gotchas

- **`-sharedDb`:** without it, each access key + region combination gets a *separate* database. That leads to "my table disappeared" confusion when two tools use different dummy keys.
- `-inMemory` is faster for tests, but loses data on restart. `-dbPath` persists (this repo stores data in `docker/dynamodb/`, which should probably be in `.gitignore`).
- Region and credentials must still be set, even though their values are ignored.
