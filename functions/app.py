import json
import os

# import requests


def lambda_handler(event, context):
    query_params = event['queryStringParameters']
    zoom_size = query_params.get('zoom_size')
    folder_name = query_params.get('folder_name')
    geojson = json.loads(event['body'])
    server_path = "server\lyon_wms.json"

    # Change directory /tmp
    os.chdir('/tmp')
    
   # Create a new .geojson file
    with open('temp.geojson', 'w') as f:
       json.dump(geojson, f)

   # Wait until the file is created
    while not os.path.exists('temp.geojson'):
       time.sleep(1)

    new_geojson_path = "tmp\temp.geojson"
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "test" : new_geojson_path
        })
    }
