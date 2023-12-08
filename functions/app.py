import json
import shutil
import io
import base64
from geo_tiles_download import get_geo_tiles
from flask import Flask, send_file
from export_zip import export_zip

def lambda_handler(event, context):
    query_params = event['queryStringParameters']
    zoom_size = query_params.get('zoom_size')
    geojson = json.loads(event['body'])
    server_path = "server/lyon_wms.json"
    with open('/tmp/temp.geojson', 'w') as f:
        json.dump(geojson, f)
    folder = '/tmp/geo_tiles'
    get_geo_tiles(server_path, folder, True,tiles=None, zoom=[zoom_size], bbox=None, geojson=['/tmp/temp.geojson'])

    return {
        "statusCode": 200,
        "body": base64.b64encode(export_zip(folder)).decode(),
        'headers': {
            'Content-Type': 'application/zip',
            'Content-Disposition': 'attachment; filename="files.zip"'
        },
        'isBase64Encoded': False
    }
