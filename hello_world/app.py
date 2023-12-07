import json

# import requests


def lambda_handler(event, context):
    query_params = event.get('queryStringParameters', {})
    a = int(query_params.get('a', 0))
    b = int(query_params.get('b', 0))
    result = a + b
    return {
        "statusCode": 200,
        "body": json.dumps({
            "result" : result
        })
    }
