"""29 - Distributed locking: a lock item with a conditional write and a lease expiry."""

import time

from botocore.exceptions import ClientError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p29-distributed-locking")

LEASE_SECONDS = 2


def acquire(resource, owner, lease=LEASE_SECONDS):
    """Take the lock if it's free OR the previous holder's lease has expired."""
    now = time.time()
    try:
        table.put_item(
            Item={
                "PK": f"LOCK#{resource}",
                "SK": "LOCK",
                "owner": owner,
                "expiresAt": int(now + lease),  # also set as the table's TTL attribute in AWS
            },
            ConditionExpression="attribute_not_exists(PK) OR expiresAt < :now",
            ExpressionAttributeValues={":now": int(now)},
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def heartbeat(resource, owner, lease=LEASE_SECONDS):
    """Extend the lease - only if we still own it."""
    table.update_item(
        Key={"PK": f"LOCK#{resource}", "SK": "LOCK"},
        UpdateExpression="SET expiresAt = :exp",
        ConditionExpression="#o = :me",
        ExpressionAttributeNames={"#o": "owner"},
        ExpressionAttributeValues={":exp": int(time.time() + lease), ":me": owner},
    )


def release(resource, owner):
    """Delete the lock - only if we still own it (never release someone else's lock)."""
    try:
        table.delete_item(
            Key={"PK": f"LOCK#{resource}", "SK": "LOCK"},
            ConditionExpression="#o = :me",
            ExpressionAttributeNames={"#o": "owner"},
            ExpressionAttributeValues={":me": owner},
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


show("worker-A acquires", acquire("invoice-run", "worker-A"))
show("worker-B tries while A holds it", acquire("invoice-run", "worker-B"))

heartbeat("invoice-run", "worker-A")
show("worker-A heartbeats; lock item", table.get_item(Key={"PK": "LOCK#invoice-run", "SK": "LOCK"})["Item"])

show("worker-A releases", release("invoice-run", "worker-A"))
show("worker-B acquires after release", acquire("invoice-run", "worker-B"))

# worker-B "crashes" (never releases). After the lease runs out, someone else can take over.
print(f"\n... worker-B crashes, waiting {LEASE_SECONDS + 1}s for the lease to expire ...")
time.sleep(LEASE_SECONDS + 1)
show("worker-C takes over the expired lock", acquire("invoice-run", "worker-C"))
show("zombie worker-B tries to release C's lock", release("invoice-run", "worker-B"))
show("lock still held by", table.get_item(Key={"PK": "LOCK#invoice-run", "SK": "LOCK"})["Item"]["owner"])
