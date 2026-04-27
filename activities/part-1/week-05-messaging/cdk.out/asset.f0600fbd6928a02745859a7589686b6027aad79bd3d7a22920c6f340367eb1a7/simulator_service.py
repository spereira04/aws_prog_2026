"""
Week 5: Messaging — Simulator Service (Starter)

TODO: Implement a service that generates telemetry events and publishes to SQS.
"""
import json
import random
import uuid
import os
from datetime import datetime, timezone

import boto3

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class SimulatorService:
    def __init__(self):
        kwargs = {"region_name": os.getenv("AWS_REGION", "us-east-1")}
        endpoint = os.getenv("AWS_ENDPOINT_URL")
        if endpoint:
            kwargs["endpoint_url"] = endpoint
        self.sqs = boto3.client("sqs", **kwargs)
        self.queue_url = os.getenv("TELEMETRY_QUEUE_URL", "")

    def generate_telemetry(self, session_key: int, driver_number: int) -> dict:
        """Generate a random telemetry event."""
        # TODO: Create a telemetry event dict with:
        # - event_type: "telemetry_update"
        # - session_key, driver_number
        # - timestamp (ISO format)
        # - data: speed, rpm, throttle, brake, drs, n_gear (random values)
        # - idempotency_key (unique ID)
        return {
            "event_type": "telemetry_update",
            "session_key": session_key,
            "driver_number": driver_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "speed": random.randint(80, 340),
                "rpm": random.randint(8000, 15000),
                # throttle y brake no pueden ser 100 al mismo tiempo pero bueno
                "throttle": random.randint(0, 100),
                "brake": random.randint(0, 100),
                "drs": random.randint(0, 1),
                "n_gear": random.randint(1, 8),
            },
            "idempotency_key": str(uuid.uuid4()),
        }

    def publish_event(self, event: dict) -> None:
        """Publish a telemetry event to SQS."""
        # TODO: Use sqs.send_message() to publish the event
        # Message body should be JSON-encoded
        self.sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(event),
        )

    def tick(self, session_key: int, driver_numbers: list) -> int:
        """Execute one simulation tick for all drivers."""
        # TODO: Generate and publish telemetry for each driver
        for driver_number in driver_numbers:
            event = self.generate_telemetry(session_key, driver_number)
            self.publish_event(event)
            logger.info(f"Published telemetry for driver {driver_number}")

        print(f"Tick done, published {len(driver_numbers)} events")
        return len(driver_numbers)
