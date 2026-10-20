"""21 - Chunking: split a big value across several items under one PK."""

import os

from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import Binary

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p21-chunking")

CHUNK_SIZE = 300 * 1024  # stay safely under the 400 KB item limit
DOC_ID = "DOC#report-2026"

blob = os.urandom(1_000_000)  # ~1 MB - too big for one item
chunks = [blob[i : i + CHUNK_SIZE] for i in range(0, len(blob), CHUNK_SIZE)]

# Write a manifest and N zero-padded chunk items (zero padding keeps sort order correct).
with table.batch_writer() as batch:
    batch.put_item(Item={"PK": DOC_ID, "SK": "MANIFEST", "chunks": len(chunks), "size": len(blob), "version": 1})
    for i, chunk in enumerate(chunks):
        batch.put_item(Item={"PK": DOC_ID, "SK": f"CHUNK#{i:04d}", "data": Binary(chunk), "version": 1})

show("Wrote", {"bytes": len(blob), "chunks": len(chunks)})

# Read: one Query returns the chunks in SK order. Query pages at 1 MB, so loop.
parts, kwargs = [], {"KeyConditionExpression": Key("PK").eq(DOC_ID) & Key("SK").begins_with("CHUNK#")}
while True:
    resp = table.query(**kwargs)
    parts.extend(item["data"].value for item in resp["Items"])
    if "LastEvaluatedKey" not in resp:
        break
    kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

manifest = table.get_item(Key={"PK": DOC_ID, "SK": "MANIFEST"})["Item"]
reassembled = b"".join(parts)
show("Reassembled", {"chunks_read": len(parts), "expected": int(manifest["chunks"]), "matches": reassembled == blob})
