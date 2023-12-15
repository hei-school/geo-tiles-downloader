import json
import shutil
import io
import os
import time
import base64
import cgi
from email import message_from_string
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


def lambda_handler(event, context):
    query_params = event.get("queryStringParameters", {})
    zoom_size = query_params.get('zoom_size')

    fp = io.BytesIO(event['body'].encode('utf-8'))
    pdict = cgi.parse_header(event['headers']['Content-Type'])[1]
    if 'boundary' in pdict:
        pdict['boundary'] = pdict['boundary'].encode('utf-8')
    pdict['CONTENT-LENGTH'] = len(event['body'])
    form_data = cgi.parse_multipart(fp, pdict)

    geojson = form_data.get('geojson')[0]
    server = form_data.get('server')[0]

    with open('/tmp/temp.geojson', 'w') as json_file:
        json.dump( json.loads(geojson.decode('utf-8')), json_file)
    with open('/tmp/server.json', 'w') as json_file:
        json.dump(json.loads(server.decode('utf-8')), json_file)

    folder = '/tmp/geo_tiles'

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