"""38 - Capacity modes: on-demand vs provisioned (+ auto scaling), and how to switch."""

from botocore.exceptions import ClientError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # for common.py

from common import client, recreate_table, show

TABLE = "p38-capacity-modes"
table = recreate_table(TABLE)  # recreate_table always starts PAY_PER_REQUEST (on-demand)


def billing(name):
    desc = client.describe_table(TableName=name)["Table"]
    return {
        "BillingMode": desc.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED"),
        "ProvisionedThroughput": {
            k: desc["ProvisionedThroughput"][k] for k in ("ReadCapacityUnits", "WriteCapacityUnits")
        },
    }


show("Start: on-demand", billing(TABLE))

# Capacity-unit maths (what you're billed for / what you provision):
#   1 RCU = one strongly consistent read/sec of up to 4 KB (or 2 eventually consistent reads)
#   1 WCU = one write/sec of up to 1 KB
#   transactions cost 2x
def rcu(item_kb, reads_per_sec, consistent=True):
    units = -(-item_kb // 4)  # ceil
    return units * reads_per_sec * (1 if consistent else 0.5)


def wcu(item_kb, writes_per_sec):
    return -(-item_kb // 1) * writes_per_sec


show(
    "Sizing for 3 KB items, 500 reads/s, 100 writes/s",
    {"RCU (strong)": rcu(3, 500), "RCU (eventual)": rcu(3, 500, consistent=False), "WCU": wcu(3, 100)},
)

# Traffic is now predictable -> switch to provisioned (AWS limits how often you can switch per 24h).
try:
    client.update_table(
        TableName=TABLE,
        BillingMode="PROVISIONED",
        ProvisionedThroughput={"ReadCapacityUnits": 250, "WriteCapacityUnits": 300},
    )
    client.get_waiter("table_exists").wait(TableName=TABLE)
    show("After switching to provisioned", billing(TABLE))
except ClientError as e:
    show("Switch failed", str(e))

# Auto scaling lives in a different service (Application Auto Scaling), which DynamoDB Local
# doesn't have. This is what you'd run in AWS - printed, not executed.
show(
    "Auto scaling setup (AWS only, not executed)",
    {
        "register_scalable_target": {
            "ServiceNamespace": "dynamodb",
            "ResourceId": f"table/{TABLE}",
            "ScalableDimension": "dynamodb:table:WriteCapacityUnits",
            "MinCapacity": 50,
            "MaxCapacity": 1000,
        },
        "put_scaling_policy": {
            "PolicyType": "TargetTrackingScaling",
            "TargetTrackingScalingPolicyConfiguration": {
                "TargetValue": 70.0,
                "PredefinedMetricSpecification": {"PredefinedMetricType": "DynamoDBWriteCapacityUtilization"},
            },
        },
    },
)

# And back to on-demand (e.g. for a spiky launch).
client.update_table(TableName=TABLE, BillingMode="PAY_PER_REQUEST")
client.get_waiter("table_exists").wait(TableName=TABLE)
show("Back to on-demand", billing(TABLE))
