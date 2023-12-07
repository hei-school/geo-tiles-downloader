import json
import shutil
from geo_tiles_download import get_geo_tiles
from flask import Flask, send_file
from export_zip import export_zip

# import requests


def lambda_handler(event, context):
    query_params = event.get('queryStringParameters', {})
    folder = '/tmp/geo_tiles/'
    get_geo_tiles(server, '/tmp/geo_tiles/', force, tiles=None, zoom=None, bbox=None, geojson=None)
    
    a = int(query_params.get('a', 0))
    b = int(query_params.get('b', 0))
    result = a + b

    ## return the zip
    ## add  
    export_zip(folder)
    zip_file_path = '/tmp/output_dir/output.zip'

    return send_file(zip_file_path, as_attachment=True, download_name='tiles.zip')
