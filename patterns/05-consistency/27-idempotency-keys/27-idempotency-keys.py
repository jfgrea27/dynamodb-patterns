"""27 - Idempotency keys: make retried requests safe."""

import time

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p27-idempotency-keys")
cond_failed = table.meta.client.exceptions.ConditionalCheckFailedException

charges = []  # stand-in for a side effect, e.g. calling a payment provider


def charge_card(idempotency_key, amount):
    key = {"PK": f"IDEMPOTENCY#{idempotency_key}", "SK": "RECORD"}

    # 1. Claim the key. Fails if a previous request already claimed it.
    try:
        table.put_item(
            Item={**key, "status": "IN_PROGRESS", "expiresAt": int(time.time()) + 24 * 3600},
            ConditionExpression="attribute_not_exists(PK)",
        )
    except cond_failed:
        record = table.get_item(Key=key, ConsistentRead=True)["Item"]
        if record["status"] == "COMPLETED":
            return record["response"]  # replay the stored result
        raise RuntimeError("request already in progress - retry later")

    # 2. Do the work once.
    charges.append(amount)
    response = {"chargeId": f"ch_{len(charges)}", "amount": amount}

    # 3. Store the result so retries get the same answer.
    table.update_item(
        Key=key,
        UpdateExpression="SET #s = :done, #r = :resp",
        ExpressionAttributeNames={"#s": "status", "#r": "response"},
        ExpressionAttributeValues={":done": "COMPLETED", ":resp": response},
    )
    return response


show("First call", charge_card("req-123", 50))
show("Client retries same key", charge_card("req-123", 50))
show("New key", charge_card("req-456", 20))
show("Card was actually charged", charges)
