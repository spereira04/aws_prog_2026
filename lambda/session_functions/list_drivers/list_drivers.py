import json
import requests

API_URL = "https://api.openf1.org/v1/drivers"

ALLOWED_FILTERS = {
    "broadcast_name",
    "country_code",
    "driver_number",
    "first_name",
    "full_name",
    "headshot_url",
    "last_name",
    "meeting_key",
    "name_acronym",
    "session_key",
    "team_colour",
    "team_name",
}

RETURN_FIELDS = {
    "driver_number",
    "full_name",
    "team_name",
    "country_code"
}


def filter_fields(items):
    return [
        {k: item[k] for k in RETURN_FIELDS if k in item}
        for item in items
    ]

def extract_request_params(event):
	params = {}
	query_params = event.get("queryStringParameters") or {}

	# Validate filters
	invalid_filters = [k for k in query_params if k not in ALLOWED_FILTERS]
	if invalid_filters:
		return {
			"statusCode": 400,
			"body": json.dumps({
				"error": "Invalid filter parameters",
				"invalid_filters": invalid_filters
			})
		}

	# Build allowed filter params
	for key, value in query_params.items():
		if value is not None:
			params[key] = value


def handler(event, context):
    try:
        params = extract_request_params(event)

        try:
            response = requests.get(API_URL, params=params, timeout=10)
        except requests.exceptions.RequestException as e:
            return {
                "statusCode": 503,
                "body": json.dumps({
                    "error": "Unable to reach OpenF1 API",
                    "details": str(e)
                })
            }

        # Upstream error
        if response.status_code != 200:
            return {
                "statusCode": 502,
                "body": json.dumps({
                    "error": "OpenF1 API returned an error",
                    "upstream_status": response.status_code
                })
            }

        drivers = response.json()
        clean_drivers = filter_fields(drivers)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "filters": params,
                "count": len(clean_drivers),
                "drivers": clean_drivers
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "details": str(e)
            })
        }