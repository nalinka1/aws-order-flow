import json
import os
from datetime import datetime, timezone

import boto3

s3 = boto3.client("s3")

BUCKET_NAME = os.environ["RECEIPTS_BUCKET_NAME"]


def handler(event, context):
    """
    Triggered by SQS (event source mapping from OrderQueue, which is
    subscribed to the OrderCreatedTopic SNS topic).

    Each SQS record wraps an SNS notification, which wraps the original
    order JSON as a string in the "Message" field.

    Does a trivial validation (amount > 0) and writes a receipt JSON
    file to S3. Raises on invalid records so SQS will NOT delete the
    message and it becomes visible for retry / eventually the DLQ,
    which is the point we want to make about at-least-once delivery.
    """
    for record in event.get("Records", []):
        sns_envelope = json.loads(record["body"])
        order = json.loads(sns_envelope["Message"])

        order_id = order["orderId"]
        amount = order["amount"]

        if amount is None or float(amount) <= 0:
            # Deliberately fail this record so SQS retries / DLQs it,
            # rather than silently swallowing a bad order.
            raise ValueError(f"Order {order_id} has invalid amount: {amount}")

        receipt = {
            "orderId": order_id,
            "customerName": order["customerName"],
            "item": order["item"],
            "amount": amount,
            "processedAt": datetime.now(timezone.utc).isoformat(),
            "status": "VALIDATED",
        }

        key = f"receipts/{order_id}.json"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps(receipt).encode("utf-8"),
            ContentType="application/json",
        )

    return {"statusCode": 200}
