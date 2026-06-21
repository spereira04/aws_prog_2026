import os
import json
import boto3
import logging

ecs_client = boto3.client('ecs')

# These environment variables will be set in your Lambda configuration
CLUSTER_NAME = os.environ.get('ECS_CLUSTER_NAME', 'f1-simulation-cluster')
TASK_DEFINITION = os.environ.get('ECS_TASK_DEFINITION', 'f1-simulator-task')
SUBNETS = os.environ.get('VPC_SUBNETS', 'subnet-xxxxxx,subnet-yyyyyy').split(',')
SECURITY_GROUP_ID = os.environ.get('SECURITY_GROUP_ID')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):

    try:
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        total_ticks = str(body.get('ticks', 300))
        num_cars = str(body.get('cars', 20))
        session_key = str(body.get('session_key', 'latest')) # Default to 'latest' if not provided

        logger.info(f"Starting simulation task for session_key {session_key} : )")

        # Trigger a brand-new Fargate task
        response = ecs_client.run_task(
            cluster=CLUSTER_NAME,
            launchType='FARGATE',
            taskDefinition=TASK_DEFINITION,
            count=1,
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': SUBNETS,
                    'securityGroups': [SECURITY_GROUP_ID],
                    'assignPublicIp': 'DISABLED' 
                }
            },
            overrides={
                'containerOverrides': [
                    {
                        'name': 'f1-simulator', # Must match the container name in your Task Definition
                        'environment': [
                            {'name': 'TICKS', 'value': total_ticks},
                            {'name': 'CARS', 'value': num_cars},
                            {'name': 'SESSION_KEY', 'value': session_key}
                        ]
                    }
                ]
            }
        )

        task_arn = response['tasks'][0]['taskArn']

        return {
            'statusCode': 202,
            'body': json.dumps({
                'status': 'Simulation container provisioned successfully',
                'task_arn': task_arn
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
