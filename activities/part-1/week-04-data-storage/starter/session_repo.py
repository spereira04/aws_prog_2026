"""
Week 4: Data Storage — Session Repository (Starter)

TODO: Implement DynamoDB operations for sessions.
"""
import boto3
import os
from botocore.exceptions import ClientError


class SessionRepository:
    def __init__(self):
        kwargs = {"region_name": os.getenv("AWS_REGION", "us-east-1")}
        endpoint = os.getenv("AWS_ENDPOINT_URL")
        if endpoint:
            kwargs["endpoint_url"] = endpoint

        self.dynamodb = boto3.resource("dynamodb", **kwargs)
        self.table = self.dynamodb.Table(
            os.getenv("SESSIONS_TABLE", "f1_sessions")
        )

    def save(self, session: dict) -> None:
        """Save a session to DynamoDB."""
        try:
            self.table.put_item(Item=session)
        except ClientError as e:
            raise RuntimeError(f"Failed to save session: {e.response['Error']['Message']}")

    def get(self, session_key: int) -> dict:
        """Get a session by session_key."""
        try:
            response = self.table.get_item(Key={"session_key": session_key})
        except ClientError as e:
            raise RuntimeError(f"Failed to get session: {e.response['Error']['Message']}")

        item = response.get("Item")
        if not item:
            raise KeyError(f"Session {session_key} not found")

        return item

    def list_all(self) -> list:
        """List all sessions."""
        try:
            response = self.table.scan()
        except ClientError as e:
            raise RuntimeError(f"Failed to get sessions: {e.response['Error']['Message']}")

        items = response.get("Items", [])

        # Handle pagination (scan only returns up to 1MB per call)
        # Insano ^^
        while "LastEvaluatedKey" in response:
            response = self.table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(response.get("Items", []))

        return items