import json
import shutil
import io
import os
import time
import base64
from io import BytesIO
from multipart import parse_form_data

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

# def extract_content_from_multipart(body):
#     fields = parse_form_data(BytesIO(body))
#     server_content = None
#     geojson_content = None

#     for field in fields:
#         if field.name == 'server':
#             server_content = field.value.decode('utf-8')
#         elif field.name == 'geojson_file':
#             geojson_content = field.value.decode('utf-8')

#     return server_content, geojson_content


def lambda_handler(event, context):
        query_params = event.get("queryStringParameters", {})
        zoom_size = query_params.get('zoom_size')
        
        payload = encoded_payload_from_event(event)
        
        byte_data = encoded_payload_from_event(event)
        decoded_string = byte_data.decode()
        first_line = decoded_string.strip().splitlines()[0]
        parts = decoded_string.split(first_line)
        server = json.loads('\n'.join(parts[1].strip().splitlines()[2:]))
        geojson = json.loads('\n'.join(parts[2].strip().splitlines()[2:]))
    
       # server_content, geojson_content = extract_content_from_multipart(encoded_payload_from_event(event))     
        with open('/tmp/temp.geojson', 'w') as json_file:
            json.dump(geojson, json_file)
        with open('/tmp/server.json', 'w') as json_file:
            json.dump(server, json_file)
            
        folder = '/tmp/geo_tiles'

        while not os.path.exists('/tmp/temp.geojson') or not os.path.exists('/tmp/server.json'):
            time.sleep(1)
        

        get_geo_tiles("/tmp/server.json", folder, True, tiles=None, zoom=[zoom_size], bbox=None, geojson=['/tmp/temp.geojson'])
        
        return {
            "statusCode": 200,
            "body": to_base64(export_zip(folder)),
            "headers": {
                'Content-Type': 'application/zip',
                'Content-Disposition': 'attachment; filename="files.zip"'
            },
            "isBase64Encoded": True
        } 

       