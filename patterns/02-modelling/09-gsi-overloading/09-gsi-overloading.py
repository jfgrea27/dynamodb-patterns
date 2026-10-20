"""09 - GSI overloading: one generic GSI (GSI1PK/GSI1SK) serves different access patterns per entity type."""

from boto3.dynamodb.conditions import Key

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import gsi, recreate_table, show

table = recreate_table("p09-gsi-overloading", gsis=[gsi("GSI1")])

# The SAME index attributes mean different things on different entity types:
#   Employee: GSI1PK=EMAIL#<email>            -> look up employee by email
#   Ticket:   GSI1PK=ASSIGNEE#<emp>, GSI1SK=<priority>#<date> -> tickets per assignee by priority
#   Office:   GSI1PK=CITY#<city>              -> offices by city
with table.batch_writer() as batch:
    batch.put_item(Item={
        "PK": "EMP#e1", "SK": "EMP#e1", "type": "Employee", "name": "Eve",
        "GSI1PK": "EMAIL#eve@acme.com", "GSI1SK": "EMP#e1",
    })
    batch.put_item(Item={
        "PK": "EMP#e2", "SK": "EMP#e2", "type": "Employee", "name": "Finn",
        "GSI1PK": "EMAIL#finn@acme.com", "GSI1SK": "EMP#e2",
    })
    for tid, emp, prio, date in [("t1", "e1", "P1", "2026-10-18"), ("t2", "e1", "P3", "2026-10-19"),
                                 ("t3", "e1", "P1", "2026-10-20"), ("t4", "e2", "P2", "2026-10-20")]:
        batch.put_item(Item={
            "PK": f"TICKET#{tid}", "SK": f"TICKET#{tid}", "type": "Ticket",
            "GSI1PK": f"ASSIGNEE#{emp}", "GSI1SK": f"{prio}#{date}",
        })
    for oid, city in [("o1", "London"), ("o2", "London"), ("o3", "Paris")]:
        batch.put_item(Item={
            "PK": f"OFFICE#{oid}", "SK": f"OFFICE#{oid}", "type": "Office",
            "GSI1PK": f"CITY#{city}", "GSI1SK": f"OFFICE#{oid}",
        })

resp = table.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq("EMAIL#eve@acme.com"))
show("Employee by email", resp["Items"][0]["name"])

resp = table.query(
    IndexName="GSI1",
    KeyConditionExpression=Key("GSI1PK").eq("ASSIGNEE#e1") & Key("GSI1SK").begins_with("P1#"),
)
show("Eve's P1 tickets", [i["PK"] for i in resp["Items"]])

resp = table.query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq("CITY#London"))
show("London offices", [i["PK"] for i in resp["Items"]])

show("Indexes on table", [g["IndexName"] for g in table.global_secondary_indexes])
