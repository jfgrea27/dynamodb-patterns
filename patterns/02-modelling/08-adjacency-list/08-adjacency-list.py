"""08 - Adjacency list: model many-to-many as edge items, query both directions."""

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import gsi, recreate_table, show

# Inverted GSI (PK<->SK swapped) lets us walk edges backwards.
table = recreate_table("p08-adjacency", gsis=[gsi("Inverted", pk="SK", sk="PK")])

# Students <-> courses. Each node has a "self" item (PK == SK).
# Each enrolment is an edge item: PK=STUDENT#x, SK=COURSE#y.
with table.batch_writer() as batch:
    for s in ["ann", "ben", "cat"]:
        batch.put_item(Item={"PK": f"STUDENT#{s}", "SK": f"STUDENT#{s}", "type": "Student", "name": s.title()})
    for c, title in [("db101", "Databases"), ("ml200", "Machine Learning")]:
        batch.put_item(Item={"PK": f"COURSE#{c}", "SK": f"COURSE#{c}", "type": "Course", "title": title})

    enrolments = [("ann", "db101"), ("ann", "ml200"), ("ben", "db101"), ("cat", "ml200")]
    for s, c in enrolments:
        batch.put_item(Item={
            "PK": f"STUDENT#{s}",
            "SK": f"COURSE#{c}",
            "type": "Enrolment",
            "grade": "A" if s == "ann" else "B",  # edges can carry their own attributes
        })

# Forward: which courses is Ann taking? (base table)
resp = table.query(KeyConditionExpression=Key("PK").eq("STUDENT#ann") & Key("SK").begins_with("COURSE#"))
show("Ann's courses", [(i["SK"], i["grade"]) for i in resp["Items"]])

# Backward: who is enrolled in db101? (inverted index: SK becomes the partition key)
resp = table.query(
    IndexName="Inverted",
    KeyConditionExpression=Key("SK").eq("COURSE#db101") & Key("PK").begins_with("STUDENT#"),
)
show("Students in db101", [i["PK"] for i in resp["Items"]])

# The node item itself also shows up in the inverted index (PK == SK).
resp = table.query(IndexName="Inverted", KeyConditionExpression=Key("SK").eq("COURSE#ml200"))
show("Everything pointing at ml200", [(i["PK"], i["type"]) for i in resp["Items"]])
