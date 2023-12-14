
import argparse
import copy
import json
import mercantile
import mimetypes
import multiprocessing
import pathlib
import queue
import requests
import supermercado

from functools import reduce
from pathlib import Path

def generate_tile_def_from_list(args_tiles):
    """
        yield [x, y, z, xmin, ymin, xmax, ymax]

        @param args_tiles
                a list of tile definition files (handlers) containing
                "x,y,z,xmin,ymin,xmax,ymax" tuple strings
    """
    for f in args_tiles:
        with f as f:
            for line in f:
                [x, y, z, *bbox] = line.strip().split(",")
                yield list(map(int,[x, y, z])) + list(map(float, bbox))

def geerate_tile_def_from_feature(features, zooms, projected):
    """
        yield [x, y, z, xmin, ymin, xmax, ymax]

        @param features
               a list  geojson features (i.e. polygon) objects
        @param zooms
                a list of zoom levels
        @param projected
                'mercator' or 'geographic'
    """
    # $ supermercado burn <zoom>
    for zoom in zooms:
        zr = zoom.split("-")
        for z in range(int(zr[0]),  int(zr[1] if len(zr) > 1 else zr[0]) + 1):
            for t in supermercado.burntiles.burn(features, z):
                tile = t.tolist()
                # $ mercantile shapes --mercator
                feature = mercantile.feature(
                    tile,
                    fid=None,
                    props={},
                    projected=projected,
                    buffer=None,
                    precision=None
                )
                bbox = feature["bbox"]
                yield tile + bbox

def generate_tile_def_from_bbox(args_bboxes, zooms, projected):
    """
        yield [x, y, z, xmin, ymin, xmax, ymax]

        @param args_bboxes
                a list of bbox definitions in comma separated string
        @param zooms
                a list of zoom levels
        @param projected
                'mercator' or 'geographic'
    """
    for f in args_bboxes:
        bbox = list(map(float, f.split(",")))
        # Assuming that zooms is a single zoom level
        for z in zooms:
            yield [0, 0, z, *bbox]

def generate_tile_def_from_area(args_areas, zooms, projected):
    """
    Générer des définitions de tuile à partir de zones géographiques.

    @param args_areas: Une liste de chemins de fichiers GeoJSON
    @param zooms: Une liste de niveaux de zoom
    @param projected: 'mercator' ou 'geographic'
    """
    
    for geojson_file in args_areas:
        with open(geojson_file) as f:
            area = json.load(f)
            for tile_def in geerate_tile_def_from_feature(area.get('features'), zooms, projected):
                # Fix: Only yield the first 4 elements (x, y, z, bbox)
                yield tile_def[:4]


def fetch_tile_worker(id, tile_def, server, output, force, stat):
    counter_total = 0
    counter_attempt = 0
    counter_ok = 0

    ext = mimetypes.guess_extension(server["parameter"]["format"])

    with requests.Session() as session:
        x, y, z, bbox = tile_def
        counter_total += 1

        output = Path(output)
        z = Path(str(z))
        x = Path(str(x))

        out_dir = output / str(z) / str(x)
        out_file = out_dir / "{}{}".format(y, ext)

        # skip already fetched tiles
        if out_file.is_file() and not force:
            return

        # copy parameter object in case of concurrency?
        params = copy.deepcopy(server["parameter"])
        params["bbox"] = ",".join(map(str, [bbox]))

        counter_attempt += 1
        r = session.get(server["url"], params=params)
        if r.ok:
            out_dir.mkdir(parents=True, exist_ok=True)
            with open(out_file, 'wb') as out:
                out.write(r.content)
                counter_ok += 1

    stat[id] = {"counter_total": counter_total,
                "counter_attempt": counter_attempt,
                "counter_ok": counter_ok}

def fetch_tiles(server, tile_def_generator, output=pathlib.Path('.'), force=False):
        statistic = {}

        for i, tile_def in enumerate(tile_def_generator):
            fetch_tile_worker(i, tile_def, server, output, force, statistic)

        def collect_result(s1, s2):
            if s1:
                return {
                    "counter_total": s1["counter_total"] + s2["counter_total"],
                    "counter_attempt": s1["counter_attempt"] + s2["counter_attempt"],
                    "counter_ok": s1["counter_ok"] + s2["counter_ok"]
                }
            else:
                return s2

        result = reduce(collect_result, statistic.values(), None)
        print("Total: {}, Ok: {}, Failed: {}, Skipped: {}".format(
            result["counter_total"],
            result["counter_ok"],
            result["counter_attempt"] - result["counter_ok"],
            result["counter_total"] - result["counter_attempt"]))

def get_geo_tiles(server, output, force, tiles=None, zoom=None, bbox=None, geojson=None):
        with open(server) as f:
            server_string = f.read()
            server = json.loads(server_string)
            print("Loaded server:", type(server), type(server_string))

        # Logique pour récupérer les tuiles en fonction des arguments facultatifs fournis le cas échéant
        if tiles is not None:
            fetch_tiles(server, generate_tile_def_from_list(tiles), output, force)
        elif zoom is not None:
            # Déterminer le système de coordonnées projetées en fonction du paramètre du serveur
            if server["parameter"]["srs"] == "EPSG:3857":
                print("1")
                projected = "mercator"
                
            elif server["parameter"]["srs"] == "EPSG:4326":
                print("2")
                projected = "geographic"
                
            else:
                print(3)
                raise argparse.ArgumentTypeError('Only EPSG:3857 and EPSG:4326 are supported.')

            if geojson is not None:
                print(4)
                fetch_tiles(server, generate_tile_def_from_area(geojson, zoom, projected), output, force)
            elif bbox is not None:
                print(6)
                fetch_tiles(server, generate_tile_def_from_bbox(bbox, zoom, projected), output, force)