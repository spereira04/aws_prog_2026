import boto3
import json
import os
import logging

from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

HEADERS = {"Content-Type": "application/json"}
RAW_DATA_INGESTION_FUNCTION = os.environ["RAW_DATA_INGESTION_FUNCTION"]

lambda_client = boto3.client('lambda')


def handler(event, context):
    query_params = event.get("queryStringParameters") or {}
    session_key = query_params.get("session_key")

    if session_key is None:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "session_key is missing"}),
            "headers": HEADERS
        }

    logger.info("Triggering ingestion for session %s", session_key)

    try:
        lambda_client.invoke(
            FunctionName=RAW_DATA_INGESTION_FUNCTION,
            InvocationType="Event",
            Payload=json.dumps({"session_key": session_key})
        )
    except (ClientError, BotoCoreError) as e:
        logger.error("Could not invoke ingestion for %s: %s", session_key, e)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Failed to trigger ingestion: {e}"}),
            "headers": HEADERS
        }

    logger.info("Ingestion triggered for session %s", session_key)
    return {
        "statusCode": 202,
        "body": json.dumps({"message": "Ingestion started", "session_key": session_key}),
        "headers": HEADERS
    }
