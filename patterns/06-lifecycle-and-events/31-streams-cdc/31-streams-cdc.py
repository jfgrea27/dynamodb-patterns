"""31 - DynamoDB Streams / CDC: react to every change (outbox, search sync, views)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show, streams_client

table = recreate_table("p31-streams-cdc", stream="NEW_AND_OLD_IMAGES")
stream_arn = table.latest_stream_arn
show("Stream ARN", stream_arn)

# Normal writes. The app never calls a second system - the stream is the outbox.
table.put_item(Item={"PK": "ORDER#o1", "SK": "META", "status": "PLACED", "total": 42})
table.update_item(
    Key={"PK": "ORDER#o1", "SK": "META"},
    UpdateExpression="SET #s = :s",
    ExpressionAttributeNames={"#s": "status"},
    ExpressionAttributeValues={":s": "SHIPPED"},
)
table.delete_item(Key={"PK": "ORDER#o1", "SK": "META"})

# In AWS a Lambda event source mapping does this polling for you.
# Here we read the stream by hand: describe -> shards -> iterator -> records.
search_index = {}  # stand-in for OpenSearch / a materialized view / an event bus


def handle(record):
    event = record["eventName"]  # INSERT | MODIFY | REMOVE
    keys = record["dynamodb"]["Keys"]
    doc_id = f'{keys["PK"]["S"]}|{keys["SK"]["S"]}'
    if event == "REMOVE":
        search_index.pop(doc_id, None)
    else:
        search_index[doc_id] = record["dynamodb"]["NewImage"]
    old = record["dynamodb"].get("OldImage", {}).get("status", {}).get("S")
    new = record["dynamodb"].get("NewImage", {}).get("status", {}).get("S")
    print(f"{event:7} {doc_id}  status: {old} -> {new}  index size={len(search_index)}")


show("Processing stream records")
shards = streams_client.describe_stream(StreamArn=stream_arn)["StreamDescription"]["Shards"]
for shard in shards:
    iterator = streams_client.get_shard_iterator(
        StreamArn=stream_arn, ShardId=shard["ShardId"], ShardIteratorType="TRIM_HORIZON"
    )["ShardIterator"]
    while iterator:
        resp = streams_client.get_records(ShardIterator=iterator, Limit=100)
        for record in resp["Records"]:
            handle(record)
        if not resp["Records"]:
            break  # caught up; a real consumer keeps polling
        iterator = resp.get("NextShardIterator")

show("Search index after replay", search_index)
