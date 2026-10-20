"""20 - Offload large blobs to S3: DynamoDB keeps metadata + a pointer, S3 keeps the bytes.

DynamoDB Local has no S3, so a local directory stands in for the bucket.
In AWS swap LocalBlobStore for boto3.client("s3").put_object / get_object.
"""

import hashlib
import os
import tempfile
import time

from botocore.exceptions import ClientError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p20-offload-s3")


class LocalBlobStore:
    """Stand-in for S3: put_object/get_object keyed by bucket + key."""

    def __init__(self, root):
        self.root = root

    def put_object(self, Bucket, Key, Body):
        path = os.path.join(self.root, Bucket, Key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(Body)

    def get_object(self, Bucket, Key):
        with open(os.path.join(self.root, Bucket, Key), "rb") as f:
            return {"Body": f.read()}


s3 = LocalBlobStore(tempfile.mkdtemp(prefix="p20-s3-"))
BUCKET = "my-docs-bucket"

# 1 MB document - far over DynamoDB's 400 KB item limit.
body = os.urandom(1024 * 1024)

# First show the failure we're avoiding.
try:
    table.put_item(Item={"PK": "DOC#too-big", "SK": "META", "body": body})
except ClientError as e:
    show("Storing 1 MB inline fails", e.response["Error"]["Message"])

# Write order matters: blob FIRST, then the pointer. A crash in between leaves an
# orphan blob (cleanable by an S3 lifecycle rule), never a pointer to nothing.
doc_id = "d1"
s3_key = f"docs/{doc_id}/v1"
s3.put_object(Bucket=BUCKET, Key=s3_key, Body=body)
table.put_item(Item={
    "PK": f"DOC#{doc_id}", "SK": "META",
    "title": "Quarterly report",
    "contentType": "application/pdf",
    "size": len(body),
    "sha256": hashlib.sha256(body).hexdigest(),
    "s3Bucket": BUCKET,
    "s3Key": s3_key,
    "uploadedAt": int(time.time()),
})

meta = table.get_item(Key={"PK": f"DOC#{doc_id}", "SK": "META"})["Item"]
show("DynamoDB item (small, queryable metadata)", meta)

# Listing/searching only touches DynamoDB; fetch the bytes only when needed.
blob = s3.get_object(Bucket=meta["s3Bucket"], Key=meta["s3Key"])["Body"]
show("Fetched blob matches checksum", hashlib.sha256(blob).hexdigest() == meta["sha256"])
