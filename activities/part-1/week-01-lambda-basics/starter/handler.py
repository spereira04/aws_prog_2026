"""
Week 1: Lambda Basics — Start Simulation Handler

TODO: Implement a Lambda function that fetches session data from the OpenF1 API.

Steps:
1. Read SESSION_KEY from environment variables
2. Call the OpenF1 API: https://api.openf1.org/v1/sessions?session_key={SESSION_KEY}
3. Return the session information as a JSON response

Hints:
- Use os.getenv() to read environment variables
- Use the requests library for HTTP calls
- Return a dict with statusCode and body keys
- Handle errors gracefully (missing env var, API failure)
"""
import json
import os
import requests


def handler(event, context):
    # TODO: Read SESSION_KEY from environment variables
    session_key = os.environ.get("SESSION_KEY")

    # TODO: Validate that SESSION_KEY is set
    if not session_key:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "SESSION_KEY not set"})
        }  # Return 400 error

    # TODO: Call the OpenF1 API to fetch session data
    # URL: https://api.openf1.org/v1/sessions?session_key={session_key}
    response = requests.get(f'https://api.openf1.org/v1/sessions?session_key={session_key}')

    # TODO: Parse the API response

    # TODO: Return the session data as a Lambda response
    # Format: {"statusCode": 200, "body": json.dumps({...})}
    return {
        "statusCode": response.status_code,
        "body": json.dumps(response.json()),
    }
