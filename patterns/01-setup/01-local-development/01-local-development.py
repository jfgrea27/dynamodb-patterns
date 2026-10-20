"""01 - Local development: DynamoDB Local in Docker, a configurable endpoint, and throwaway test tables."""

import os
import uuid
from contextlib import contextmanager

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import log_requests, show

# 1. One switch decides local vs AWS. In a real app, default to None so prod uses the normal
#    credential chain + region; this playground defaults to the docker container.
ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT", "http://localhost:8000")


def make_resource():
    kwargs = {"region_name": os.environ.get("AWS_REGION", "us-east-1")}
    if ENDPOINT:
        # DynamoDB Local accepts any credentials. Note: without -sharedDb, the
        # access key + region pick which separate database you see.
        kwargs |= {"endpoint_url": ENDPOINT, "aws_access_key_id": "dummy", "aws_secret_access_key": "dummy"}
    return boto3.resource("dynamodb", **kwargs)


ddb = make_resource()
log_requests(ddb.meta.client)  # print each request, like the other scripts

# 2. Fail fast with a helpful message if the container isn't running.
try:
    tables = ddb.meta.client.list_tables()["TableNames"]
    show(f"Connected to {ENDPOINT}", {"existing tables": len(tables)})
except EndpointConnectionError:
    raise SystemExit("DynamoDB Local isn't running. Start it with: just up")


# 3. Tests: create a uniquely named table, yield it, always delete it.
#    Same table definition as prod (ideally loaded from your IaC), so tests catch key/GSI mistakes.
@contextmanager
def temp_table(prefix="p01-test"):
    name = f"{prefix}-{uuid.uuid4().hex[:8]}"
    table = ddb.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()
    try:
        yield table
    finally:
        table.delete()


def test_create_user(table):
    table.put_item(Item={"PK": "USER#1", "SK": "PROFILE", "name": "Ada"})
    assert table.get_item(Key={"PK": "USER#1", "SK": "PROFILE"})["Item"]["name"] == "Ada"


def test_duplicate_user_rejected(table):
    table.put_item(Item={"PK": "USER#1", "SK": "PROFILE"})
    try:
        table.put_item(Item={"PK": "USER#1", "SK": "PROFILE"}, ConditionExpression="attribute_not_exists(PK)")
    except ClientError as e:
        assert e.response["Error"]["Code"] == "ConditionalCheckFailedException"
    else:
        raise AssertionError("expected a conditional check failure")


show("Running tests, each against its own throwaway table")
for test in (test_create_user, test_duplicate_user_rejected):
    with temp_table() as t:
        test(t)
        print(f"  PASS {test.__name__}  (table {t.name})")

leftovers = [n for n in ddb.meta.client.list_tables()["TableNames"] if n.startswith("p01-test")]
show("Test tables left behind", leftovers)
