"""26 - Unique constraints on non-key attributes: sentinel items written in the same transaction."""

# Note: `client` comes from the boto3 resource, so it takes plain Python values (no {"S": ...} wrappers).

from botocore.exceptions import ClientError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import client, recreate_table, show

TABLE = "p26-unique-constraints"
table = recreate_table(TABLE)


def create_user(user_id, email):
    """Write the user and an EMAIL# sentinel atomically. Either both land or neither does."""
    client.transact_write_items(
        TransactItems=[
            {
                "Put": {
                    "TableName": TABLE,
                    "Item": {"PK": f"USER#{user_id}", "SK": "PROFILE", "email": email},
                    "ConditionExpression": "attribute_not_exists(PK)",
                }
            },
            {
                "Put": {
                    "TableName": TABLE,
                    "Item": {"PK": f"EMAIL#{email.lower()}", "SK": "EMAIL", "user_id": user_id},
                    "ConditionExpression": "attribute_not_exists(PK)",
                }
            },
        ]
    )


def change_email(user_id, old, new):
    """Swap the sentinel: delete old, create new (guarded), update the user - all in one transaction."""
    client.transact_write_items(
        TransactItems=[
            {"Delete": {"TableName": TABLE, "Key": {"PK": f"EMAIL#{old.lower()}", "SK": "EMAIL"}}},
            {
                "Put": {
                    "TableName": TABLE,
                    "Item": {"PK": f"EMAIL#{new.lower()}", "SK": "EMAIL", "user_id": user_id},
                    "ConditionExpression": "attribute_not_exists(PK)",
                }
            },
            {
                "Update": {
                    "TableName": TABLE,
                    "Key": {"PK": f"USER#{user_id}", "SK": "PROFILE"},
                    "UpdateExpression": "SET email = :e",
                    "ConditionExpression": "email = :old",
                    "ExpressionAttributeValues": {":e": new, ":old": old},
                }
            },
        ]
    )


def attempt(label, fn):
    try:
        fn()
        show(label, "OK")
    except ClientError as e:
        reasons = [r.get("Code") for r in e.response.get("CancellationReasons", [])]
        show(label, {"error": e.response["Error"]["Code"], "reasons": reasons})


attempt("alice signs up with a@x.com", lambda: create_user("alice", "a@x.com"))
attempt("bob tries A@x.com (same email, different case)", lambda: create_user("bob", "A@x.com"))
attempt("bob signs up with b@x.com", lambda: create_user("bob", "b@x.com"))
attempt("bob changes email to a@x.com (taken)", lambda: change_email("bob", "b@x.com", "a@x.com"))
attempt("bob changes email to bob@x.com", lambda: change_email("bob", "b@x.com", "bob@x.com"))

# Bonus: the sentinel doubles as a "lookup user by email" index - no GSI needed.
show("Who owns bob@x.com?", table.get_item(Key={"PK": "EMAIL#bob@x.com", "SK": "EMAIL"})["Item"])
show("All items", sorted(f'{i["PK"]} | {i["SK"]}' for i in table.scan()["Items"]))
