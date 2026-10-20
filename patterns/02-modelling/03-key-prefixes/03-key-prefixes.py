"""03 - Key prefixes / key overloading: ENTITY#id keys avoid collisions and self-describe."""

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import recreate_table, show

table = recreate_table("p03-key-prefixes")

# Without prefixes, a user "42" and an org "42" would collide on PK="42".
# With prefixes, they live in different partitions and keys are readable.
with table.batch_writer() as batch:
    batch.put_item(Item={"PK": "USER#42", "SK": "USER#42", "type": "User", "userId": "42", "name": "Dana"})
    batch.put_item(Item={"PK": "ORG#42", "SK": "ORG#42", "type": "Org", "orgId": "42", "name": "Acme"})
    batch.put_item(Item={"PK": "ORG#42", "SK": "MEMBER#USER#42", "type": "Membership", "role": "admin"})
    batch.put_item(Item={"PK": "ORG#42", "SK": "PROJECT#p1", "type": "Project", "name": "Rocket"})


# Small helpers keep key building in one place instead of f-strings everywhere.
def user_key(user_id):
    return {"PK": f"USER#{user_id}", "SK": f"USER#{user_id}"}


def org_pk(org_id):
    return f"ORG#{org_id}"


show("User 42", table.get_item(Key=user_key("42"))["Item"])

resp = table.query(KeyConditionExpression=Key("PK").eq(org_pk("42")))
show("Org 42 item collection", [(i["SK"], i["type"]) for i in resp["Items"]])

resp = table.query(KeyConditionExpression=Key("PK").eq(org_pk("42")) & Key("SK").begins_with("MEMBER#"))
show("Org 42 members only", [i["SK"] for i in resp["Items"]])

# Parsing a key back is possible, but prefer storing the id as a plain attribute.
pk = "ORG#42"
entity, _, ident = pk.partition("#")
show("Parsed key", {"entity": entity, "id": ident})
