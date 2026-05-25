"""
Week 5: Messaging — Event Consumer Lambda (Starter)

TODO: Implement SQS consumer that processes telemetry events.
"""
import json
import os
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

table = boto3.resource("dynamodb").Table(os.environ.get("LIVE_STATE_TABLE", "f1_live_state"))


def handler(event, context):
    """Process SQS messages containing telemetry events."""
    # TODO: Iterate over event["Records"]
    # TODO: Parse each record's body as JSON
    # TODO: Process the telemetry event (update DynamoDB live state)
    # TODO: Return batchItemFailures for any failed records

    batch_item_failures = []

    for record in event["Records"]:
        logger.log(record)
        try:
            body = json.loads(record["body"])
            table.put_item(Item={
                "session_key": body["session_key"],
                "driver_number": str(body["driver_number"]),
                "timestamp": body["timestamp"],
                **body.get("data", {}),
            })
            logger.info(f"Updated live state for driver {body['driver_number']}")
        except Exception as e:
            logger.error(f"Error processing record {record.get('messageId')}: {e}")
            batch_item_failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": batch_item_failures}
