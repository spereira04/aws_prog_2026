"""
Week 4: Data Storage — CDK Stack (Starter)

TODO: Create DynamoDB tables and S3 bucket for F1 Telemetry data.
"""
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
)
from constructs import Construct

class DataStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # TODO: Create f1_sessions DynamoDB table
        # Partition Key: session_key (Number)
        # Billing Mode: PAY_PER_REQUEST
        f1_sessions = dynamodb.Table(self, id='f1-sessions',
                        partition_key=dynamodb.Attribute(
                            name='session_key',
                            type=dynamodb.AttributeType.NUMBER                 
                        ),
                        billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
                    )

        # TODO: Create f1_driver_stats DynamoDB table
        # Partition Key: session_key (Number)
        # Sort Key: driver_number (Number)
        f1_driver_stats = dynamodb.Table(self, id='f1_driver_stats',
                        partition_key=dynamodb.Attribute(
                            name='session_key',
                            type=dynamodb.AttributeType.NUMBER                 
                        ),
                        sort_key=dynamodb.Attribute(
                            name='driver_number',
                            type=dynamodb.AttributeType.NUMBER                 
                        ),

                    )

        # TODO: Create f1-raw-data S3 bucket
        f1_raw_data = s3.Bucket(self, id='f1_raw_data')

        pass
