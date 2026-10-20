"""40 - Global tables: multi-region active-active replication with last-writer-wins."""

import time

from botocore.exceptions import ClientError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import client, recreate_table, show

TABLE = "p40-global-tables"
recreate_table(TABLE, stream="NEW_AND_OLD_IMAGES")  # global tables need streams (AWS turns them on for you)

# The real call (version 2019.11.21): add a replica region to an existing table.
try:
    client.update_table(TableName=TABLE, ReplicaUpdates=[{"Create": {"RegionName": "eu-west-1"}}])
    show("Replica added")
except ClientError as e:
    # DynamoDB Local ignores ReplicaUpdates and answers "Nothing to update".
    show("Add replica: not supported by DynamoDB Local", e.response["Error"].get("Message"))

# --- Simulation: two regions, async replication, last-writer-wins on conflicts ---
# Each "region" is a dict. Replication copies an item if its timestamp is newer.
regions = {"us-east-1": {}, "eu-west-1": {}}
replication_log = []  # (from_region, key, item) waiting to be applied - async!


def write(region, key, item):
    item = {**item, "_ts": time.time_ns(), "_region": region}  # AWS uses an internal timestamp
    regions[region][key] = item
    for other in regions:
        if other != region:
            replication_log.append((other, key, item))
    print(f"{region:10} wrote {key}: {item['status']}")


def replicate():
    while replication_log:
        target, key, item = replication_log.pop(0)
        current = regions[target].get(key)
        if current is None or item["_ts"] > current["_ts"]:
            regions[target][key] = item  # last writer wins
        else:
            print(f"  {target}: dropped older write from {item['_region']} ({item['status']})")


def view():
    return {r: {k: v["status"] for k, v in d.items()} for r, d in regions.items()}


show("Normal case: write in one region, read anywhere (after replication)")
write("us-east-1", "ORDER#o1", {"status": "PLACED"})
show("Before replication (eu-west-1 is stale)", view())
replicate()
show("After replication", view())

show("Conflict: both regions update the same item before replicating")
write("us-east-1", "ORDER#o1", {"status": "CANCELLED"})
write("eu-west-1", "ORDER#o1", {"status": "SHIPPED"})  # later timestamp -> wins everywhere
replicate()
show("Converged (CANCELLED was silently lost!)", view())

show("Mitigation: give each item a home region and only write there")
HOME = {"ORDER#o2": "eu-west-1"}  # e.g. based on where the customer lives
write(HOME["ORDER#o2"], "ORDER#o2", {"status": "PLACED"})
write(HOME["ORDER#o2"], "ORDER#o2", {"status": "PAID"})
replicate()
show("No conflicts possible", view())
