"""
Week 5: Messaging — CDK Stack (Starter)

TODO: Wire up the full pipeline:
  EventBridge -> engine_handler -> SQS -> event_consumer -> DynamoDB (f1_live_state)
"""
import os

from aws_cdk import (
    Stack,
    Duration,
    aws_sqs as sqs,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as _lambda,
    aws_lambda_event_sources as lambda_events,
    aws_dynamodb as dynamodb,
)
from constructs import Construct


class MessagingStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # TODO: Create Dead Letter Queue
        # Name: f1-telemetry-events-dlq, retention: 14 days
        dlq = sqs.Queue(
            self,
            "TelemetryDLQ",
            queue_name="f1-telemetry-events-dlq",
            retention_period=Duration.days(14),
        )

        # TODO: Create main Telemetry Queue
        # Name: f1-telemetry-events, visibility timeout: 60s, DLQ max receive count: 3
        telemetry_queue = sqs.Queue(
            self,
            "TelemetryQueue",
            queue_name="f1-telemetry-events",
            visibility_timeout=Duration.seconds(60),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=dlq,
            ),
        )

        # TODO: Import the existing f1_live_state DynamoDB table
        # Hint: dynamodb.Table.from_table_name(self, "LiveStateTable", "f1_live_state")
        live_state_table = dynamodb.Table.from_table_name(self, "LiveStateTable", "f1_live_state")

        # TODO: Create the consumer Lambda (event_consumer.handler)
        # - Runtime: Python 3.12
        # - Code asset: this folder (os.path.dirname(os.path.abspath(__file__)))
        # - Env: LIVE_STATE_TABLE=f1_live_state
        # - Grant the live_state table read/write to this function
        # - Add an SqsEventSource(self.telemetry_queue, batch_size=10)
        consumer_fn = _lambda.Function(
            self,
            "EventConsumer",
            function_name="f1-event-consumer",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="event_consumer.handler",
            code=_lambda.Code.from_asset(os.path.dirname(os.path.abspath(__file__))),
            environment={
                "LIVE_STATE_TABLE": "f1_live_state",
            },
        )
        live_state_table.grant_read_write_data(consumer_fn)
        consumer_fn.add_event_source(lambda_events.SqsEventSource(telemetry_queue, batch_size=10))

        # TODO: Create the engine Lambda (engine_handler.handler)
        # - Runtime: Python 3.12
        # - Same code asset folder
        # - Env: TELEMETRY_QUEUE_URL=<queue url>, SIMULATOR_SESSION_KEY, SIMULATOR_DRIVERS
        # - Grant send_messages on the telemetry queue
        engine_fn = _lambda.Function(
            self,
            "EngineHandler",
            function_name="f1-engine-handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="engine_handler.handler",
            code=_lambda.Code.from_asset(os.path.dirname(os.path.abspath(__file__))),
            environment={
                "TELEMETRY_QUEUE_URL": telemetry_queue.queue_url,
                "SIMULATOR_SESSION_KEY": "9468",
                "SIMULATOR_DRIVERS": "1,4,11,16",
            },
        )
        telemetry_queue.grant_send_messages(engine_fn)

        # TODO: Create EventBridge Rule
        # Name: f1-simulator-tick
        # Schedule: Duration.minutes(1)  (NOTE: rate() requires whole minutes — seconds will fail)
        # Initially disabled
        # Target: the engine Lambda (targets.LambdaFunction(engine_fn))
        events.Rule(
            self,
            "SimulatorTick",
            rule_name="f1-simulator-tick",
            schedule=events.Schedule.rate(Duration.minutes(1)),
            enabled=False,
            targets=[targets.LambdaFunction(engine_fn)],
        )
