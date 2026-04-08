from aws_cdk import (
    Duration,
    Stack,
    aws_events as events,
)
from constructs import Construct


class MessagingStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        events.Rule(
            self,
            "FiveSecondRuleTrigger",
            schedule=events.Schedule.rate(Duration.seconds(5)),
            enabled=False,  # disabled by default
        )