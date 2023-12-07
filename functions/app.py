import json
import shutil
from geo_tiles_download import get_geo_tiles

# import requests


def lambda_handler(event, context):
    query_params = event.get('queryStringParameters', {})
    geo_tiles_download(server, '/tmp/geo_tiles/', force, tiles=None, zoom=None, bbox=None, geojson=None)
    return {
        "statusCode": 200,
        "body": "zipped geo tiles created successfully"
    }
