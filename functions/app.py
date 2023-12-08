import json
import shutil
from geo_tiles_download import get_geo_tiles
from flask import Flask, send_file
from export_zip import export_zip

# import requests



def lambda_handler(event, context):
    query_params = event['queryStringParameters']
    zoom_size = query_params.get('zoom_size')
    geojson = json.loads(event['body'])
    server_path = "server/lyon_wms.json"
    with open('/tmp/temp.geojson', 'w') as f:
        json.dump(geojson, f)
    folder = '/tmp/geo_tiles'
    get_geo_tiles(server_path, folder, True,tiles=None, zoom=[zoom_size], bbox=None, geojson=['/tmp/temp.geojson'])

    export_zip(folder)
    zip_file_path = '/tmp/output.zip'

    return send_file(zip_file_path, as_attachment=True, download_name='tiles.zip')
