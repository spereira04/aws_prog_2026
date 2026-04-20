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

    drivers = []

    try:
        query_kwargs = {
            "KeyConditionExpression": (Key("PK").eq(f"SESSION#{session_key}") &
        Key("SK").begins_with(f"#METADATA#DRIVER#"))
        }

        while True:
            result = table.query(**query_kwargs)
            drivers.extend(result.get("Items", []))

            # handle pagination
            last_key = result.get("LastEvaluatedKey")
            if not last_key:
                break

            query_kwargs["ExclusiveStartKey"] = last_key

    except (ClientError, BotoCoreError) as e:
        logger.error(f"DynamoDB query failed: {e}")
        return response(500, {"message": "Database error"})

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return response(500, {"message": "Internal server error"})

    logger.info(f"Fetched {len(drivers)} sessions")

    return response(200, drivers)

#Epico esto
def response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body, default=int)
    }

