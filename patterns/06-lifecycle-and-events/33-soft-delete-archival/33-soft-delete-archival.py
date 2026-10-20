"""33 - Soft delete & archival: mark deleted, hide from indexes, let TTL + Streams archive to S3."""

import json
import time

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import client, gsi, recreate_table, show, streams_client

TABLE = "p33-soft-delete-archival"
table = recreate_table(TABLE, gsis=[gsi("GSI1")], stream="OLD_IMAGE")

try:
    client.update_time_to_live(
        TableName=TABLE, TimeToLiveSpecification={"Enabled": True, "AttributeName": "expiresAt"}
    )
    show("TTL enabled on expiresAt")
except ClientError as e:
    show("TTL not supported here", str(e))

# Active docs appear in GSI1 ("docs by folder"). GSI1PK is what makes them visible there.
for doc_id, title in [("d1", "Q3 plan"), ("d2", "Old draft"), ("d3", "Budget")]:
    table.put_item(
        Item={"PK": f"DOC#{doc_id}", "SK": "META", "title": title, "GSI1PK": "FOLDER#work", "GSI1SK": f"DOC#{doc_id}"}
    )


def list_folder():
    resp = table.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq("FOLDER#work"))
    return [i["title"] for i in resp["Items"]]


show("Folder before delete", list_folder())

# Soft delete: keep the item (undo is possible), but
#   - mark it deleted
#   - REMOVE the GSI keys so it drops out of the sparse index (pattern 10)
#   - set a TTL so DynamoDB hard-deletes it in ~30 days
RETENTION = 30 * 24 * 3600
table.update_item(
    Key={"PK": "DOC#d2", "SK": "META"},
    UpdateExpression="SET deletedAt = :now, expiresAt = :exp REMOVE GSI1PK, GSI1SK",
    ExpressionAttributeValues={":now": int(time.time()), ":exp": int(time.time()) + RETENTION},
)
show("Folder after soft delete (d2 hidden)", list_folder())
show("d2 is still there for undo / trash view", table.get_item(Key={"PK": "DOC#d2", "SK": "META"})["Item"])

# Later, TTL hard-deletes the item. DynamoDB Local doesn't run the TTL sweeper,
# so we simulate the expiry with a normal delete.
table.delete_item(Key={"PK": "DOC#d2", "SK": "META"})

# Stream consumer: archive every REMOVE to S3 (a dict stands in for the bucket).
# In AWS, TTL deletes carry userIdentity.principalId == "dynamodb.amazonaws.com".
fake_s3 = {}
shards = streams_client.describe_stream(StreamArn=table.latest_stream_arn)["StreamDescription"]["Shards"]
for shard in shards:
    it = streams_client.get_shard_iterator(
        StreamArn=table.latest_stream_arn, ShardId=shard["ShardId"], ShardIteratorType="TRIM_HORIZON"
    )["ShardIterator"]
    while it:
        resp = streams_client.get_records(ShardIterator=it)
        for r in resp["Records"]:
            if r["eventName"] != "REMOVE":
                continue
            by_ttl = r.get("userIdentity", {}).get("principalId") == "dynamodb.amazonaws.com"
            key = f'archive/{r["dynamodb"]["Keys"]["PK"]["S"]}.json'
            fake_s3[key] = json.dumps(r["dynamodb"]["OldImage"])
            print(f"archived {key} (deleted by TTL: {by_ttl})")
        if not resp["Records"]:
            break
        it = resp.get("NextShardIterator")

show("Fake S3 bucket", fake_s3)
