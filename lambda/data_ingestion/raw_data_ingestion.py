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
BUCKET_NAME = os.environ.get('S3_BUCKET')

s3_client = boto3.client('s3')
event_client = boto3.client('events')

HEADERS = {"Content-Type": "application/json"}


def fetch(url, params=None, max_retries=10):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=15, headers={"Connection": "close"})
        except requests.Timeout:
            logger.warning("Request timed out on attempt %s/%s for %s", attempt + 1, max_retries, url)
            if attempt + 1 == max_retries:
                raise RequestException(f"Request timed out after {max_retries} attempts for {url}")
            time.sleep(2)
            continue

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "10")
            try:
                wait = min(int(retry_after), 10)
            except ValueError:
                wait = 10
            logger.info("Rate limited on attempt %s/%s, waiting %ss", attempt + 1, max_retries, wait)
            time.sleep(wait)
            continue

        if response.status_code in (500, 502, 503, 504):
            logger.warning("Server error %s on attempt %s/%s, retrying", response.status_code, attempt + 1, max_retries)
            if attempt + 1 == max_retries:
                raise RequestException(f"Server error {response.status_code} after {max_retries} attempts for {url}")
            time.sleep(2)
            continue

        response.raise_for_status()
        return response.json()

    raise RequestException(f"Max retries ({max_retries}) exceeded for {url}")


def is_already_ingested(session_key):
    try:
        s3_client.head_object(Bucket=BUCKET_NAME, Key=f'sessions/{session_key}/session.json')
        return True
    except ClientError as e:
        if e.response['Error']['Code'] in ('404', 'NoSuchKey'):
            return False
        raise


def handler(event, context):
    logger.info("Event received: %s", json.dumps(event))

    session_key = event.get("session_key")

    if is_already_ingested(session_key):
        logger.info("Session %s already ingested, skipping", session_key)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Already ingested"}),
            "headers": HEADERS
        }

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
            time.sleep(0.5)
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Could not save drivers for session {session_key} ERROR {e}")


def ingest_laps(session_key, driver_number):
    logger.info(f"Fetching laps for driver {driver_number}")

    laps = fetch(BASE_URL + "/laps", params={"session_key": session_key, "driver_number": driver_number})

    logger.info(f"Fetched {len(laps)} laps for driver {driver_number}, saving to S3")
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
    logger.info(f"Fetching positions for driver {driver_number}")

    positions = fetch(BASE_URL + "/position", params={"session_key": session_key, "driver_number": driver_number})

    logger.info(f"Fetched {len(positions)} positions for driver {driver_number}, saving to S3")
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
                    "Source": "process.data.ingest",
                    "DetailType": "json.ingested",
                    "Detail": json.dumps({
                        "session_key": session_key
                    })
                }
            ]
        )
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Could not publish event for {session_key} ERROR: {e}")
