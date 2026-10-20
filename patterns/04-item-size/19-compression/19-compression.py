"""19 - Compression: gzip large attributes and store them as Binary."""

import gzip
import json

from boto3.dynamodb.types import Binary

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p19-compression")

# A chatty JSON document (e.g. a transcript) - text compresses very well.
transcript = [{"turn": i, "speaker": "agent" if i % 2 else "caller", "text": "Hello, how can I help you today? " * 5} for i in range(2500)]
raw = json.dumps(transcript).encode()
compressed = gzip.compress(raw)

show("Sizes", {"raw_bytes": len(raw), "gzipped_bytes": len(compressed), "ratio": round(len(raw) / len(compressed), 1)})

# Uncompressed, the item is over the 400 KB limit and DynamoDB rejects it.
try:
    table.put_item(Item={"PK": "CALL#c1", "SK": "TRANSCRIPT", "body": raw.decode()})
    show("Uncompressed put", "succeeded")
except Exception as e:
    show("Uncompressed put failed", str(e)[:120])

# Store compressed. Keep queryable fields (status, duration) as plain attributes.
table.put_item(
    Item={
        "PK": "CALL#c1",
        "SK": "TRANSCRIPT",
        "status": "completed",
        "turns": len(transcript),
        "body_gz": Binary(compressed),
        "encoding": "gzip+json",
    }
)

item = table.get_item(Key={"PK": "CALL#c1", "SK": "TRANSCRIPT"})["Item"]
restored = json.loads(gzip.decompress(item["body_gz"].value))
show("Read back", {"status": item["status"], "turns": len(restored), "first_turn": restored[0]})
