import time

import boto3

import json
import requests
import os
import logging

from botocore.exceptions import BotoCoreError, ClientError
from requests import RequestException
from requests.adapters import HTTPAdapter
from urllib3 import Retry

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BASE_URL = os.getenv("OPENF1_BASE_URL", "https://api.openf1.org/v1")
BUCKET_NAME = os.environ.get('S3_BUCKET')

s3_client = boto3.client('s3')
event_client = boto3.client('events')

HEADERS = {"Content-Type": "application/json"}


session = requests.Session()

retry_strategy = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
)

session.mount("https://", HTTPAdapter(max_retries=retry_strategy))

def fetch(url, params=None):
    while True:
        response = session.get(url, params=params)
        if response.status_code == 429:
            wait = int(response.headers.get("Retry-After", 10))
            logger.info("Rate limited, waiting %ss", wait)
            time.sleep(wait)
            continue
        response.raise_for_status()
        return response.json()

def handler(event, context):
    query_params = event.get("queryStringParameters") or {}

    session_key = query_params.get("session_key")

    logger.info(f"Starting data ingestion for session {session_key}")

    try:
        ingest_sessions(session_key)
        publish_event(session_key)
    except RequestException as e:
        logger.error(f"Request error detected, cannot finish data ingestion {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Error {e}"}),
            "headers": HEADERS
        }
    logger.info("Ingestion finished")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Ingestion finished"}),
        "headers": HEADERS
    }

def ingest_sessions(session_key):

    if session_key is None:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "session_key is missing"}),
            "headers": HEADERS
        }

    sessions = fetch(BASE_URL+f"/sessions", params={"session_key": session_key})

    # response = requests.get(BASE_URL+f"/sessions", params={"session_key": session_key})
    # response.raise_for_status()

    # sessions = response.json()
    print("Sessions requested")
    logger.info("Sessions requested")
    for session in sessions:
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
    drivers = fetch(BASE_URL + "/drivers", params={"session_key": session_key})
    # response = requests.get(BASE_URL + "/drivers", params={"session_key": session_key})
    # response.raise_for_status()

    # drivers = response.json()
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
            ingest_positions(session_key, driver["driver_number"])
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Could not save drivers for session {session_key} ERROR {e}")


def ingest_laps(session_key, driver_number):
    laps = fetch(BASE_URL + "/laps", params={"session_key": session_key, "driver_number": driver_number})
    # response = requests.get(BASE_URL + "/laps", params={"session_key": session_key, "driver_number": driver_number})
    # response.raise_for_status()

    # laps = response.json()

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

def ingest_positions(session_key, driver_number):
    positions = fetch(BASE_URL + "/position", params={"session_key": session_key, "driver_number": driver_number})
    # response = requests.get(BASE_URL + "/position", params={"session_key": session_key, "driver_number": driver_number})
    # response.raise_for_status()

    # positions = response.json()
    try:
        s3_client.put_object(
            Body=json.dumps(positions),
            Bucket=BUCKET_NAME,
            Key=f'sessions/{session_key}/drivers/{driver_number}/positions.json',
            ContentType='application/json'
        )
        logger.info(f"Saved driver {driver_number} positions")
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Could not ingest positions of driver {driver_number} in {session_key} ERROR: {e}")

def publish_event(session_key):
    try:
        event_client.put_events(
            Entries=[
                {
                    "Source": "raw.data.ingest",
                    "DetailType": "json.ingested",
                    "Detail": json.dumps({
                        "session_key": session_key
                    })
                }
            ]
        )
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Could not publish event for {session_key} ERROR: {e}")
