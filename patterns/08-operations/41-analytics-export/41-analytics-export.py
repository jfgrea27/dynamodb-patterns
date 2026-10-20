"""41 - Analytics outside DynamoDB: export to S3 and query there (Athena/Glue/Redshift), not on the table."""

import gzip
import json
import random
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import client, recreate_table, show

TABLE = "p41-analytics-export"
table = recreate_table(TABLE)

random.seed(1)
with table.batch_writer() as w:
    for i in range(500):
        w.put_item(
            Item={
                "PK": f"ORDER#{i:04}",
                "SK": "META",
                "country": random.choice(["UK", "US", "DE", "FR"]),
                "total": random.randint(5, 200),
            }
        )

# The real thing: a managed export of a PITR snapshot to S3. Uses no table capacity.
table_arn = client.describe_table(TableName=TABLE)["Table"]["TableArn"]
try:
    client.export_table_to_point_in_time(
        TableArn=table_arn, S3Bucket="my-analytics-bucket", S3Prefix="exports/orders", ExportFormat="DYNAMODB_JSON"
    )
except ClientError as e:
    show("ExportTableToPointInTime: not supported by DynamoDB Local", e.response["Error"]["Code"])

# --- Local stand-in: parallel scan -> gzipped DynamoDB-JSON files in a folder ("the S3 prefix") ---
export_dir = Path(tempfile.mkdtemp(prefix="p41-export-")) / "data"
export_dir.mkdir(parents=True)
SEGMENTS = 4
ser = TypeSerializer()


def export_segment(segment):
    path = export_dir / f"segment-{segment}.json.gz"
    kwargs = dict(TableName=TABLE, Segment=segment, TotalSegments=SEGMENTS)
    count = 0
    with gzip.open(path, "wt") as f:
        while True:
            resp = client.scan(**kwargs)  # clients are thread-safe; resource objects are not
            for item in resp["Items"]:
                # same line format as a real DYNAMODB_JSON export
                f.write(json.dumps({"Item": {k: ser.serialize(v) for k, v in item.items()}}, default=str) + "\n")
                count += 1
            if "LastEvaluatedKey" not in resp:
                break
            kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return count


with ThreadPoolExecutor(SEGMENTS) as pool:
    counts = list(pool.map(export_segment, range(SEGMENTS)))
show("Exported", {"dir": str(export_dir), "items per segment": counts})

# --- "Athena": SELECT country, COUNT(*), SUM(total) FROM orders GROUP BY country ---
agg = defaultdict(lambda: {"orders": 0, "revenue": 0})
for path in export_dir.glob("*.json.gz"):
    with gzip.open(path, "rt") as f:
        for line in f:
            item = json.loads(line)["Item"]
            row = agg[item["country"]["S"]]
            row["orders"] += 1
            row["revenue"] += int(item["total"]["N"])
show("Revenue by country (computed off the table)", dict(sorted(agg.items())))
