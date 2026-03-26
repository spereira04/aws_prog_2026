import json
import requests

BASE_URL = "https://api.openf1.org/v1/sessions"

ALLOWED_PARAMS = {
    "circuit_key",
    "circuit_short_name",
    "country_code",
    "country_key",
    "country_name",
    "date_end",
    "date_start",
    "gmt_offset",
    "location",
    "meeting_key",
    "session_key",
    "session_name",
    "session_type",
    "year",
}

def extract_request_params(event):
    query_params = event.get("queryStringParameters") or {}
    params = {}

    for key,value in query_params.items():
        if key in ALLOWED_PARAMS and value is not None:
            params[key] = value

    return params

def handler(event, context):
    params = extract_request_params(event)
    response = requests.get(BASE_URL, params=params, timeout=10)

    sessions = response.json()

    return {
        "statusCode": response.status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "filters": params,
            "count": len(sessions),
            "sessions": sessions
        })
    }