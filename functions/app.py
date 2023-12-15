import json
import shutil
import io
import os
import time
import base64
from geo_tiles_download import get_geo_tiles
from flask import Flask, send_file
from export_zip import export_zip

def to_base64(content):
    return base64.b64encode(content).decode()

def case_insensitive_obj_to_serializable_dict(obj):
    return json.loads(json.dumps(dict(obj)))

def encoded_payload_from_event(event):
    payload = event.get("body", None)
    if payload is None:
        return None
    elif event.get("isBase64Encoded", False):
        return base64.b64decode(payload)
    else:
        return payload.encode("utf-8")

def lambda_handler(event, context):
        server_path = "server/lyon_wms.json"
        query_params = event.get("queryStringParameters", {})
        zoom_size = query_params.get('zoom_size')

        with open('/tmp/temp.geojson', 'w') as f:
            json.dump(encoded_payload_from_event(event).decode(), f)
        folder = '/tmp/geo_tiles'

        while not os.path.exists('/tmp/temp.geojson'):
            time.sleep(1)

        get_geo_tiles(server=server_path, output=folder, force=True, tiles=None, zoom=[zoom_size], bbox=None, geojson=['/tmp/temp.geojson'])
        
        return {
            "statusCode": 200,
            "body": to_base64(export_zip(folder)),
            "headers": {
                'Content-Type': 'application/zip',
                'Content-Disposition': 'attachment; filename="files.zip"'
            },
            "isBase64Encoded": True
        } 

       