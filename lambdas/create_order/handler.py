import json
import os
import uuid
from datetime import datetime, timezone

import boto3

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

TABLE_NAME = os.environ["ORDERS_TABLE_NAME"]
TOPIC_ARN = os.environ["ORDER_CREATED_TOPIC_ARN"]

table = dynamodb.Table(TABLE_NAME)


def handler(event, context):
    """
    Triggered by API Gateway POST /order.
    Writes the order to DynamoDB, then publishes an OrderCreated event to SNS.
    """
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"message": "Invalid JSON body"})

    customer_name = body.get("customerName")
    item = body.get("item")
    amount = body.get("amount")

    if not customer_name or not item or amount is None:
        return _response(
            400, {"message": "customerName, item, and amount are required"}
        )

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return _response(400, {"message": "amount must be numeric"})

    order_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    order_item = {
        "orderId": order_id,
        "customerName": customer_name,
        "item": item,
        "amount": amount,
        "createdAt": created_at,
    }

    table.put_item(Item=order_item)

    sns.publish(
        TopicArn=TOPIC_ARN,
        Message=json.dumps(order_item),
        MessageAttributes={
            "eventType": {"DataType": "String", "StringValue": "OrderCreated"}
        },
    )

    return _response(201, order_item)


def _response(status_code, body_dict):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body_dict),
    }
