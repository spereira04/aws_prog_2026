import json
import os
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

REQUIRED_FIELDS = {"userId", "name", "email"}


def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"message": "El body no es un JSON válido."})

    missing = REQUIRED_FIELDS - body.keys()
    if missing:
        return _response(400, {"message": f"Faltan campos requeridos: {', '.join(missing)}"})

    user_item = {
        "userId": str(body["userId"]).strip(),
        "name":   str(body["name"]).strip(),
        "email":  str(body["email"]).strip(),
    }

    extra_keys = body.keys() - REQUIRED_FIELDS
    for key in extra_keys:
        user_item[key] = body[key]

    try:
        table.put_item(
            Item=user_item,
            ConditionExpression="attribute_not_exists(userId)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _response(409, {"message": f"El usuario '{user_item['userId']}' ya existe."})
        print(f"[ERROR] DynamoDB: {e}")
        return _response(500, {"message": "Error al guardar en la base de datos.", "detail": str(e)})
    except Exception as e:
        print(f"[ERROR] {e}")
        return _response(500, {"message": "Error interno del servidor.", "detail": str(e)})

    return _response(201, {"message": "Usuario creado exitosamente.", "user": user_item})


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }