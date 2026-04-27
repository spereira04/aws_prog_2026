import aws_cdk as cdk
from starter.messaging_stack import MessagingStack  # match the actual class name in your file

app = cdk.App()
MessagingStack(app, "MessagingStack")
app.synth()