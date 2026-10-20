"""32 - Streams-maintained aggregates: keep counts/totals up to date on write, not on read."""

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show, streams_client

table = recreate_table("p32-streams-aggregates", stream="NEW_AND_OLD_IMAGES")


def drain_stream(stream_arn):
    """Yield every record currently on the stream (a Lambda trigger does this in AWS)."""
    shards = streams_client.describe_stream(StreamArn=stream_arn)["StreamDescription"]["Shards"]
    for shard in shards:
        iterator = streams_client.get_shard_iterator(
            StreamArn=stream_arn, ShardId=shard["ShardId"], ShardIteratorType="TRIM_HORIZON"
        )["ShardIterator"]
        while iterator:
            resp = streams_client.get_records(ShardIterator=iterator, Limit=100)
            yield from resp["Records"]
            if not resp["Records"]:
                break
            iterator = resp.get("NextShardIterator")


# Writers only write orders. They never touch the aggregate item.
orders = [("o1", 42), ("o2", 17), ("o3", 99)]
for order_id, total in orders:
    table.put_item(Item={"PK": "STORE#s1", "SK": f"ORDER#{order_id}", "type": "Order", "total": total})
table.update_item(  # change o2's total: aggregate must apply the diff
    Key={"PK": "STORE#s1", "SK": "ORDER#o2"},
    UpdateExpression="SET #t = :t",
    ExpressionAttributeNames={"#t": "total"},
    ExpressionAttributeValues={":t": 20},
)
table.delete_item(Key={"PK": "STORE#s1", "SK": "ORDER#o3"})


def apply(record):
    """Turn one change into a delta and ADD it to the aggregate item."""
    img_old = record["dynamodb"].get("OldImage", {})
    img_new = record["dynamodb"].get("NewImage", {})
    if (img_new or img_old).get("type", {}).get("S") != "Order":
        return  # ignore our own aggregate writes (they're on the stream too!)

    old_total = int(img_old["total"]["N"]) if img_old else 0
    new_total = int(img_new["total"]["N"]) if img_new else 0
    count_delta = {"INSERT": 1, "REMOVE": -1}.get(record["eventName"], 0)

    store = (img_new or img_old)["PK"]["S"]
    table.update_item(
        Key={"PK": store, "SK": "STATS"},
        UpdateExpression="ADD orderCount :c, revenue :r",
        ExpressionAttributeValues={":c": count_delta, ":r": new_total - old_total},
    )
    print(f'{record["eventName"]:7} count {count_delta:+d}  revenue {new_total - old_total:+d}')


show("Consuming stream")
for record in drain_stream(table.latest_stream_arn):
    apply(record)

show("Aggregate item (read with one GetItem)", table.get_item(Key={"PK": "STORE#s1", "SK": "STATS"})["Item"])

# Sanity check against the slow way: query everything and sum.
orders_now = table.query(
    KeyConditionExpression=Key("PK").eq("STORE#s1") & Key("SK").begins_with("ORDER#")
)["Items"]
show("Recomputed from orders", {"orderCount": len(orders_now), "revenue": sum(o["total"] for o in orders_now)})
