"""
Week 2: API Gateway — Session Handlers

TODO: Implement three API endpoints:
1. GET /sessions — List 2024 race sessions from OpenF1
2. GET /sessions/{session_key} — Get a specific session from OpenF1
3. POST /sessions/{session_key}/ingest — Fetch session + driver data from OpenF1

Hints:
- Path parameters: event["pathParameters"]["session_key"]
- Query parameters: event.get("queryStringParameters") or {}
- Request body: json.loads(event["body"])
- Always include Content-Type header in response
- Catch requests.RequestException for API errors
"""
import json
import logging
import os

import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

OPENF1_BASE_URL = os.getenv("OPENF1_BASE_URL", "https://api.openf1.org")
HEADERS = {"Content-Type": "application/json"}


def list_sessions(event, context):
    """GET /sessions — Return list of 2024 race sessions from OpenF1."""
    # TODO: Call the OpenF1 API: GET /v1/sessions?session_type=Race&year=2024
    session_type = 'Race'
    year = '2024'
    response = requests.get(f'{OPENF1_BASE_URL}/v1/sessions?session_type={session_type}&year={year}')
    # TODO: Extract key fields from each session (session_key, session_name,
    #       session_type, circuit_short_name, date_start)

    if response.status_code != 200:
        return {
            "statusCode": response.status_code,
            "body": json.dumps(response.json())
        }

    data = response.json()

    filtered = [
        {
            "session_key": session["session_key"],
            "session_name": session["session_name"],
            "session_type": session["session_type"],
            "circuit_short_name": session["circuit_short_name"],
            "date_start": session["date_start"]
        }
        for session in data
    ]

    # TODO: Return {"statusCode": 200, "body": json.dumps({"sessions": [...]}), "headers": HEADERS}
    # TODO: Catch requests.RequestException and return 500
    return {
        "statusCode": 200,
        "body": json.dumps({'sessions': filtered}),
        "headers": HEADERS,
    }


def get_session(event, context):
    """GET /sessions/{session_key} — Get session details from OpenF1."""
    # TODO: Extract session_key from event["pathParameters"]["session_key"]
    # TODO: Call the OpenF1 API: GET /v1/sessions?session_key={session_key}
    session_key = event['pathParameters']['session_key']

    response = requests.get(f'{OPENF1_BASE_URL}/v1/sessions?session_key={session_key}')

    # TODO: Return 404 if no session found
    # TODO: Return the session details with status 200
    # TODO: Catch requests.RequestException and return 500
    return {
        "statusCode": response.status_code,
        "body": json.dumps(response.json()),
        "headers": HEADERS
    }


def ingest_session(event, context):
    """POST /sessions/{session_key}/ingest — Fetch session and driver data."""
    # TODO: Extract session_key from event["pathParameters"]["session_key"]
    session_key = event['pathParameters']['session_key']
    # TODO: Fetch session from OpenF1: GET /v1/sessions?session_key={session_key}
    session_response = requests.get(f'{OPENF1_BASE_URL}/v1/sessions?session_key={session_key}')
    # TODO: Return 404 if no session found
    # TODO: Fetch drivers from OpenF1: GET /v1/drivers?session_key={session_key}
    drivers_response = requests.get(f'{OPENF1_BASE_URL}/v1/drivers?session_key={session_key}')
    # TODO: Return a summary: session_key, session_name, drivers_found count,
    #       and list of drivers (driver_number, name_acronym)
    # TODO: Catch requests.RequestException and return 500
    sessions = session_response.json()
    session_drivers = drivers_response.json()

    response = {}
    for session in sessions:
        response['session_key'] = session['session_key']
        response['session_name'] = session['session_name']
        response['drivers_found'] = len(session_drivers)
        response['drivers'] = [{'driver_number': driver['driver_number'], 'name_acronym': driver['name_acronym']} for driver in session_drivers]

    return {
        "statusCode": 200,
        "body": json.dumps(response),
        "headers": HEADERS,
    }
