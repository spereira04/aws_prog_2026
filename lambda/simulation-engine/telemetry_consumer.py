import os
import json
import boto3
import sys
import logging
from datetime import datetime
from prometheus_client import start_http_server, Gauge

# 1. Configuration
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
METRICS_PORT = int(os.environ.get("METRICS_PORT", 8000))

# Initialize SQS
sqs = boto3.client("sqs", region_name=AWS_REGION)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("telemetry-consumer")

# 2. Prometheus Metrics
DRIVER_POSITION = Gauge('f1_driver_position', 'Current position', ['driver_number', 'driver_name', 'session_key'])
DRIVER_SPEED = Gauge('f1_driver_speed_kmh', 'Current speed', ['driver_number', 'driver_name', 'session_key'])
DRIVER_LAP = Gauge('f1_driver_lap_number', 'Current lap number', ['driver_number', 'driver_name', 'session_key'])
DRIVER_RACE_TIME = Gauge('f1_driver_race_time_seconds', 'Simulated race timestamp (Unix Epoch seconds)', ['driver_number', 'driver_name', 'session_key'])

def process_messages():
    """Poll SQS and update Prometheus metrics."""
    logger.info("Listening for telemetry on SQS...")
    
    while True:
        try:
            # Long polling
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
                AttributeNames=['All']
            )

            if 'Messages' in response:
                for msg in response['Messages']:
                    data = json.loads(msg['Body'])
                    
                    # Update Prometheus Gauges
                    DRIVER_POSITION.labels(
                        driver_number=data['driver_number'],
                        driver_name=data['driver_name'],
                        session_key=data['session_key']
                    ).set(data['position'])
                    
                    DRIVER_SPEED.labels(
                        driver_number=data['driver_number'],
                        driver_name=data['driver_name'],
                        session_key=data['session_key']
                    ).set(data['speed_kmh'])
                    
                    DRIVER_LAP.labels(
                        driver_number=data['driver_number'],
                        driver_name=data['driver_name'],
                        session_key=data['session_key']
                    ).set(data['lap_number'])

                    # Parse simulated race time to epoch timestamp
                    date_start = data.get('date_start')
                    if date_start:
                        try:
                            dt = datetime.fromisoformat(date_start.replace("Z", "+00:00"))
                            DRIVER_RACE_TIME.labels(
                                driver_number=data['driver_number'],
                                driver_name=data['driver_name'],
                                session_key=data['session_key']
                            ).set(dt.timestamp())
                        except Exception as parse_err:
                            logger.error(f"Error parsing date_start {date_start}: {parse_err}")

                    # Delete message from queue
                    sqs.delete_message(
                        QueueUrl=SQS_QUEUE_URL,
                        ReceiptHandle=msg['ReceiptHandle']
                    )
                
                logger.info(f"Processed {len(response['Messages'])} telemetry updates.")

        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")

if __name__ == "__main__":
    # Start Prometheus Exporter
    start_http_server(METRICS_PORT)
    logger.info(f"📊 Prometheus exporter started on port {METRICS_PORT}")
    
    # Start SQS Polling
    process_messages()
