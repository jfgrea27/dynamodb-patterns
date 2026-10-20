"""23 - Optimistic locking: a version attribute + conditional write prevents lost updates."""

from botocore.exceptions import ClientError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p23-optimistic-locking")
key = {"PK": "ACCOUNT#a1", "SK": "META"}
table.put_item(Item={**key, "balance": 100, "version": 1})


def save(item, expected_version):
    """Write the item only if nobody else bumped the version since we read it."""
    table.put_item(
        Item={**item, "version": expected_version + 1},
        ConditionExpression="version = :v",
        ExpressionAttributeValues={":v": expected_version},
    )


# Two clients read the same version...
a = table.get_item(Key=key)["Item"]
b = table.get_item(Key=key)["Item"]

# ...client A writes first and wins.
save({**a, "balance": a["balance"] + 50}, a["version"])
show("A deposited 50", table.get_item(Key=key)["Item"])

# ...client B's write is based on stale data and is rejected instead of silently overwriting A.
try:
    save({**b, "balance": b["balance"] - 30}, b["version"])
except ClientError as e:
    show("B rejected", e.response["Error"]["Code"])


# Standard fix: re-read, re-apply the change, retry.
def update_with_retry(change, attempts=3):
    for _ in range(attempts):
        current = table.get_item(Key=key, ConsistentRead=True)["Item"]
        try:
            save(change(current), current["version"])
            return
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
    raise RuntimeError("gave up after retries")


update_with_retry(lambda cur: {**cur, "balance": cur["balance"] - 30})
show("B retried on fresh data", table.get_item(Key=key)["Item"])
