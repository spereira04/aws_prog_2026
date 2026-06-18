import os
import json
import boto3
import sys
import logging
import uuid
import time
from decimal import Decimal

# 1. Configuration
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE")
SESSION_KEY = os.environ.get("SESSION_KEY")

# Initialize AWS
sqs = boto3.client("sqs", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("f1-simulator")

def get_session_drivers(session_key):
    """Fetch driver metadata."""
    logger.info(f"Fetching drivers for session: {session_key}")
    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('PK').eq(f"SESSION#{session_key}") & 
                               boto3.dynamodb.conditions.Key('SK').begins_with("#METADATA#DRIVER#")
    )
    return response.get('Items', [])

def get_driver_lap_data(session_key, driver_number):
    """Fetch lap data."""
    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('PK').eq(f"SESSION#{session_key}") & 
                               boto3.dynamodb.conditions.Key('SK').begins_with(f"DRIVER#{driver_number}#LAP#")
    )
    items = response.get('Items', [])
    items.sort(key=lambda x: int(x.get('lap_number', 0)))
    return items

def main():
    if not SESSION_KEY:
        logger.error("No SESSION_KEY provided. Exiting.")
        return

    drivers = get_session_drivers(SESSION_KEY)
    if not drivers:
        logger.error(f"No drivers found for session {SESSION_KEY}.")
        return

    driver_laps = {str(d['driver_number']): get_driver_lap_data(SESSION_KEY, d['driver_number']) for d in drivers}
    max_session_laps = max([len(laps) for laps in driver_laps.values()])
    
    logger.info(f"🏎️ Replaying Session {SESSION_KEY} via SQS. Max Laps: {max_session_laps}")

    try:
        for lap_idx in range(max_session_laps):
            for d in drivers:
                d_num = str(d['driver_number'])
                laps = driver_laps[d_num]
                
                if lap_idx < len(laps):
                    current_lap = laps[lap_idx]
                    
                    # Explicit conversion to avoid ANY Decimal objects
                    telemetry = {
                        "session_key": str(SESSION_KEY),
                        "driver_number": d_num,
                        "driver_name": str(d.get('last_name', d_num)),
                        "lap_number": int(current_lap.get('lap_number', 0)),
                        "position": int(current_lap.get('position', 0)),
                        "speed_kmh": float(current_lap.get('i1_speed', 0))
                    }

                    sqs.send_message(
                        QueueUrl=SQS_QUEUE_URL,
                        MessageBody=json.dumps(telemetry),
                        MessageGroupId=f"SIM-{SESSION_KEY}",
                        MessageDeduplicationId=str(uuid.uuid4())
                    )

            logger.info(f"Sent Lap {lap_idx + 1}/{max_session_laps} to SQS")
            time.sleep(5)

        logger.info(f"🏁 Replay of session {SESSION_KEY} finished.")

    except Exception as e:
        logger.error(f"❌ Simulation Error: {e}")

if __name__ == "__main__":
    main()
