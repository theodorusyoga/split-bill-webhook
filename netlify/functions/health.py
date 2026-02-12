import json


def handler(event, context):
    """Health check endpoint."""
    return {"statusCode": 200, "body": json.dumps({"status": "ok"})}
