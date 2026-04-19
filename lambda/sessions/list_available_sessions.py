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
    sessions = []

    try:
        query_kwargs = {
            "KeyConditionExpression": Key("PK").eq("SESSION")
        }

        while True:
            result = table.query(**query_kwargs)
            sessions.extend(result.get("Items", []))

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

    logger.info(f"Fetched {len(sessions)} sessions")

    return response(200, sessions)

#Epico esto
def response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body, default=int)
    }

