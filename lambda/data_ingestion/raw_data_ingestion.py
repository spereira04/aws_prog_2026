import time

import boto3

import json
import requests
import os
import logging

from botocore.exceptions import BotoCoreError, ClientError
from requests import RequestException

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BASE_URL = os.getenv("OPENF1_BASE_URL", "https://api.openf1.org/v1")
BUCKET_NAME = os.environ.get('MY_S3_BUCKET')

s3_client = boto3.client('s3')

HEADERS = {"Content-Type": "application/json"}

def handler(event, context):
    query_params = event.get("queryStringParameters") or {}

    start_date = query_params.get("sessions_start_date")
    end_date = query_params.get("sessions_end_date")

    logger.info(f"Starting data ingestion for sessions between {start_date} and {end_date}")

    try:
        ingest_sessions(query_params.get("sessions_start_date"), query_params.get("sessions_end_date"))
    except RequestException as e:
        logger.error(f"Request error detected, cannot finish data ingestion {e}")
    logger.info("Ingestion finished")
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Ingestion finished"}),
        "headers": HEADERS
    }

def ingest_sessions(start_date, end_date):

    if start_date is None or end_date is None:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "sessions_start_date or sessions_end_date missing"}),
            "headers": HEADERS
        }

    response = requests.get(BASE_URL+f"/sessions?date_start>={start_date}&date_end<={end_date}")
    response.raise_for_status()

    sessions = response.json()
    print("Sessions requested")
    logger.info("Sessions requested")
    for session in sessions:
        session_key = session["session_key"]
        try:
            s3_client.put_object(
                Body=json.dumps(session),
                Bucket=BUCKET_NAME,
                Key=f'sessions/{session_key}/session.json',
                ContentType='application/json'
            )

            logger.info(f"Saved session {session_key}")
            ingest_drivers(session_key)
        except(ClientError, BotoCoreError) as e:
            logger.error(f"Could not save session {session_key} ERROR: {e}")
    return None


def ingest_drivers(session_key):
    response = requests.get(BASE_URL + "/drivers", params={"session_key": session_key})
    response.raise_for_status()

    drivers = response.json()
    try:
        s3_client.put_object(
            Body=json.dumps(drivers),
            Bucket=BUCKET_NAME,
            Key=f'sessions/{session_key}/drivers/driversRace.json',
            ContentType='application/json'
        )
        logger.info(f"Saved drivers from session {session_key}")

        for driver in drivers:
            ingest_laps(session_key, driver["driver_number"])
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Could not save drivers for session {session_key} ERROR {e}")


def ingest_laps(session_key, driver_number):
    response = requests.get(BASE_URL + "/laps", params={"session_key": session_key, "driver_number": driver_number})
    response.raise_for_status()

    laps = response.json()

    try:
        s3_client.put_object(
            Body=json.dumps(laps),
            Bucket=BUCKET_NAME,
            Key=f'sessions/{session_key}/drivers/{driver_number}/laps.json',
            ContentType='application/json'
        )
        logger.info(f"Saved driver {driver_number} laps")
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Could not ingest lap of driver {driver_number} in {session_key} ERROR: {e}")
