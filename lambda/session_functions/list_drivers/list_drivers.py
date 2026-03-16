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


def handler(event, context):
	params = {}

	# Read query parameters if invoked via API Gateway
	query_params = event.get("queryStringParameters") or {}

	# Only allow supported filters
	for key, value in query_params.items():
		if key in ALLOWED_FILTERS and value is not None:
			params[key] = value

	response = requests.get(API_URL, params=params, timeout=10)

	if response.status_code != 200:
		return {
			"statusCode": 502,
			"body": json.dumps({
				"error": "Failed to fetch drivers",
				"status_code": response.status_code
			})
		}

	drivers = response.json()

	return {
		"statusCode": 200,
		"body": json.dumps({
			"filters": params,
			"count": len(drivers),
			"drivers": drivers
		})
	}
