"""06 - Sortable IDs (ISO-8601 / ULID-style) so the latest items come first."""

import os
import time
import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p06-sortable-ids")

CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid(ts_ms=None):
    """Minimal ULID: 48-bit ms timestamp + 80 random bits, Crockford base32 (26 chars).

    Use the `python-ulid` package in real code.
    """
    ts_ms = int(time.time() * 1000) if ts_ms is None else ts_ms
    n = (ts_ms << 80) | int.from_bytes(os.urandom(10), "big")
    return "".join(CROCKFORD[(n >> (5 * i)) & 31] for i in reversed(range(26)))


base = int(datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp() * 1000)
with table.batch_writer() as batch:
    for day in [3, 1, 7, 2, 5]:  # written out of order on purpose
        ts = base + day * 86_400_000
        iso = datetime.fromtimestamp(ts / 1000, timezone.utc).isoformat(timespec="milliseconds")
        # Option A: ISO-8601 timestamp + random suffix to keep keys unique
        batch.put_item(Item={"PK": "ROOM#general", "SK": f"MSG#{iso}#{uuid.uuid4().hex[:6]}", "text": f"Oct {1 + day}"})
        # Option B: ULID - one sortable, unique, compact ID
        batch.put_item(Item={"PK": "ROOM#random", "SK": f"MSG#{ulid(ts)}", "text": f"Oct {1 + day}"})

resp = table.query(KeyConditionExpression=Key("PK").eq("ROOM#general"), ScanIndexForward=False, Limit=3)
show("Latest 3 (ISO-8601 keys, newest first)", [(i["SK"], i["text"]) for i in resp["Items"]])

resp = table.query(KeyConditionExpression=Key("PK").eq("ROOM#random"), ScanIndexForward=False, Limit=3)
show("Latest 3 (ULID keys, newest first)", [(i["SK"], i["text"]) for i in resp["Items"]])

# Time-range query works because the keys sort lexicographically by time.
resp = table.query(
    KeyConditionExpression=Key("PK").eq("ROOM#general")
    & Key("SK").between("MSG#2026-10-02", "MSG#2026-10-05~"),
)
show("Messages between 2 and 5 Oct", [i["text"] for i in resp["Items"]])

# Why UUIDv4 doesn't work: random order.
show("uuid4 values are not time-ordered", sorted(str(uuid.uuid4())[:8] for _ in range(3)))
