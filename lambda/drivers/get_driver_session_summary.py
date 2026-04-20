import os
import logging
import json

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

table = boto3.resource("dynamodb").Table(os.environ["DYNAMODB_TABLE"])

def handler(event, context):
    query_params = event.get("queryStringParameters") or {}

    session_key = query_params.get("session_key")
    if not session_key:
        return response(400, {"message": "session_key is required"})

    driver_id = query_params.get("driver_id")
    if not driver_id:
        return response(400, {"message": "driver_id is required"})

    try:
        result = table.query(
            KeyConditionExpression=
                Key("PK").eq(f"SESSION#{session_key}") &
                Key("SK").eq(f"#METADATA#DRIVER#{driver_id}")
        )

        items = result.get("Items", [])

        if not items:
            return response(404, {"message": "Driver not found"})

        return response(200, items[0])

    except (ClientError, BotoCoreError) as e:
        logger.error(f"DynamoDB query failed: {e}")
        return response(500, {"message": "Database error"})

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return response(500, {"message": "Internal server error"})

def response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body, default=int)
    }

