"""Shared helpers for the pattern scripts. Run a pattern with: just run NN"""

import atexit
import json
import os
import re
import threading
from decimal import Decimal

import boto3
from boto3.dynamodb.types import TypeDeserializer

ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT", "http://localhost:8000")
REGION = "us-east-1"

_session_kwargs = dict(
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id="dummy",
    aws_secret_access_key="dummy",
)

# ---------------------------------------------------------------------------
# Request logging: every DynamoDB call is printed as ">>> Operation table" with
# its expressions rendered with the real names/values substituted in.
# Set LOG_REQUESTS=0 to turn it off.
# ---------------------------------------------------------------------------

_deserializer = TypeDeserializer()
_log_lock = threading.RLock()
_run = {"op": None, "count": 0}  # collapses long runs of the same operation (seeding data)
_SHOW_PER_RUN = 3
_SKIP_OPS = {"CreateTable", "DeleteTable", "DescribeTable", "ListTables"}  # setup / waiters
_EXPRESSIONS = [
    ("KeyConditionExpression", "key"),
    ("FilterExpression", "filter"),
    ("ConditionExpression", "condition"),
    ("UpdateExpression", "update"),
    ("ProjectionExpression", "projection"),
]
_SCALARS = [
    "IndexName", "Select", "Limit", "ScanIndexForward", "ConsistentRead", "Segment",
    "TotalSegments", "ReturnValues", "ReturnValuesOnConditionCheckFailure", "ClientRequestToken",
]


def _plain(value):
    """Typed {"S": ...} -> plain Python. Values that aren't typed are returned as-is."""
    try:
        return _deserializer.deserialize(value)
    except (TypeError, AttributeError, ValueError, KeyError):
        return value


def _fmt(value, limit=60):
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {_fmt(v, limit)}" for k, v in value.items()) + "}"
    if isinstance(value, (list, tuple)):
        inner = ", ".join(_fmt(v, limit) for v in value[:5])
        return "[" + inner + (f", ... +{len(value) - 5}" if len(value) > 5 else "") + "]"
    if isinstance(value, (bytes, bytearray)) or hasattr(value, "value"):
        return f"<{len(getattr(value, 'value', value))} bytes>"
    if isinstance(value, Decimal):
        return str(_default(value))
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "...'"


def _attrs(item):
    """A Key/Item map with typed values -> readable string."""
    return _fmt({k: _plain(v) for k, v in item.items()})


def _render_expression(expr, names, values):
    def sub(m):
        token = m.group(0)
        if token.startswith("#"):
            return names.get(token, token)
        return _fmt(_plain(values[token])) if token in values else token

    return re.sub(r"[#:][A-Za-z0-9_]+", sub, expr)


def _describe(params, indent="    "):
    lines = []
    names = params.get("ExpressionAttributeNames", {})
    values = params.get("ExpressionAttributeValues", {})
    if "Key" in params:
        lines.append(f"key:        {_attrs(params['Key'])}")
    if "Item" in params:
        lines.append(f"item:       {_attrs(params['Item'])}")
    for field, label in _EXPRESSIONS:
        if field in params:
            lines.append(f"{label + ':':<11} {_render_expression(params[field], names, values)}")
    for field in _SCALARS:
        if field in params:
            lines.append(f"{field + ':':<11} {params[field]}")
    if "ExclusiveStartKey" in params:
        lines.append(f"startKey:   {_attrs(params['ExclusiveStartKey'])}")
    return [indent + line for line in lines]


def _describe_request(op, params):
    table = params.get("TableName", "")
    lines = [f"\n>>> {op} {table}".rstrip()]

    if op in ("TransactWriteItems", "TransactGetItems"):
        for entry in params["TransactItems"]:
            (sub_op, sub_params), = entry.items()
            lines.append(f"    - {sub_op} {sub_params.get('TableName', '')}")
            lines += _describe(sub_params, indent="        ")
    elif op == "BatchWriteItem":
        for tbl, reqs in params["RequestItems"].items():
            puts = sum("PutRequest" in r for r in reqs)
            lines.append(f"    {tbl}: {puts} puts, {len(reqs) - puts} deletes")
    elif op == "BatchGetItem":
        for tbl, spec in params["RequestItems"].items():
            lines.append(f"    {tbl}: {len(spec['Keys'])} keys, e.g. {_attrs(spec['Keys'][0])}")
    elif op == "ExecuteStatement":
        lines.append(f"    statement: {params['Statement']}")
    else:
        lines += _describe(params)
    return lines


def _flush_run():
    hidden = _run["count"] - _SHOW_PER_RUN
    if hidden > 0:
        print(f"    ... (+{hidden} more {_run['op']} calls not shown)")
    _run["op"], _run["count"] = None, 0


def _log_request(params, model, **_):
    if os.environ.get("LOG_REQUESTS", "1") == "0" or model.name in _SKIP_OPS:
        return
    with _log_lock:
        if model.name != _run["op"]:
            _flush_run()
            _run["op"] = model.name
        _run["count"] += 1
        if _run["count"] <= _SHOW_PER_RUN:
            print("\n".join(_describe_request(model.name, params)))


def log_requests(boto_client):
    """Print every request this client makes. Already applied to `client`/`streams_client`."""
    # before-parameter-build runs after boto3 has turned Key()/Attr() conditions into
    # expression strings, so we see exactly what is sent.
    service = boto_client.meta.service_model.service_id.hyphenize()
    boto_client.meta.events.register_last(f"before-parameter-build.{service}", _log_request)
    return boto_client


atexit.register(lambda: _flush_run())

dynamodb = boto3.resource("dynamodb", **_session_kwargs)
client = log_requests(dynamodb.meta.client)
streams_client = log_requests(boto3.client("dynamodbstreams", **_session_kwargs))


def gsi(name, pk=None, sk=None, projection="ALL", include=None):
    """GSI spec. Defaults to the overloaded naming convention: <name>PK / <name>SK.

    Pass sk=False for a partition-key-only index.
    """
    return {
        "name": name,
        "pk": pk or f"{name}PK",
        "sk": None if sk is False else (sk or f"{name}SK"),
        "projection": projection,
        "include": include or [],
    }


def recreate_table(name, gsis=(), pk="PK", sk="SK", stream=None):
    """Drop (if present) and create a PAY_PER_REQUEST table with string keys.

    gsis:   list of gsi(...) specs
    stream: e.g. "NEW_AND_OLD_IMAGES" to enable DynamoDB Streams
    """
    try:
        client.delete_table(TableName=name)
        client.get_waiter("table_not_exists").wait(TableName=name)
    except client.exceptions.ResourceNotFoundException:
        pass

    key_schema = [{"AttributeName": pk, "KeyType": "HASH"}]
    attrs = {pk}
    if sk:
        key_schema.append({"AttributeName": sk, "KeyType": "RANGE"})
        attrs.add(sk)

    kwargs = dict(TableName=name, KeySchema=key_schema, BillingMode="PAY_PER_REQUEST")

    if gsis:
        indexes = []
        for g in gsis:
            ks = [{"AttributeName": g["pk"], "KeyType": "HASH"}]
            attrs.add(g["pk"])
            if g["sk"]:
                ks.append({"AttributeName": g["sk"], "KeyType": "RANGE"})
                attrs.add(g["sk"])
            projection = {"ProjectionType": g["projection"]}
            if g["projection"] == "INCLUDE":
                projection["NonKeyAttributes"] = g["include"]
            indexes.append({"IndexName": g["name"], "KeySchema": ks, "Projection": projection})
        kwargs["GlobalSecondaryIndexes"] = indexes

    kwargs["AttributeDefinitions"] = [{"AttributeName": a, "AttributeType": "S"} for a in sorted(attrs)]

    if stream:
        kwargs["StreamSpecification"] = {"StreamEnabled": True, "StreamViewType": stream}

    table = dynamodb.create_table(**kwargs)
    table.wait_until_exists()
    return table


def _default(o):
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    if isinstance(o, (bytes, bytearray)):
        return f"<{len(o)} bytes>"
    if isinstance(o, set):
        return sorted(o)
    if hasattr(o, "value"):  # boto3 Binary
        return f"<{len(o.value)} bytes>"
    return str(o)


def show(title, obj=None):
    """Print a section header and (optionally) a pretty JSON dump."""
    with _log_lock:
        _flush_run()
    print(f"\n=== {title} ===")
    if obj is not None:
        print(json.dumps(obj, indent=2, default=_default))
