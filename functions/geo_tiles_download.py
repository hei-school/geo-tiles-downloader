#!/usr/bin/env python3

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
    features = [f for f in supermercado.super_utils.filter_features(features)]
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
        gj = {
            "type": "Feature",
            "bbox": bbox,
            "geometry": {
                 "type": "Polygon",
                 "coordinates": [[
                    [bbox[0], bbox[1]], [bbox[2], bbox[1]], [bbox[2], bbox[3]], [bbox[0], bbox[3]], [bbox[0], bbox[1]]
                ]]
            }
        }
        yield from geerate_tile_def_from_feature([gj], zooms, projected)

def generate_tile_def_from_area(args_areas, zooms, projected):
    """
        yield [x, y, z, xmin, ymin, xmax, ymax]

        @param args_areas
                a list of files defining polygon areas with geojson
        @param zooms
                a list of zoom levels
        @param projected
                'mercator' or 'geographic'
    """
    for f in args_areas:
        with f as f:
            area = json.load(f)
            yield from geerate_tile_def_from_feature(area["features"], zooms, projected)

def fetch_tile_worker(id, input_queue, stop_event, server, output, force, stat):
    counter_total = 0
    counter_attempt = 0
    counter_ok =  0

    ext = mimetypes.guess_extension(server["parameter"]["format"])

    with requests.Session() as session:
        while not stop_event.is_set():
            try:
                x, y, z, bbox = input_queue.get(True, 1)
                #print (id, x, y, z)
                counter_total += 1

                out_dir = output / str(z) / str(x)
                out_file = out_dir / "{}{}".format(y, ext)

                # skip already fetched tiles
                if out_file.is_file() and not force:
                    input_queue.task_done()
                    continue

                # copy parameter object in case of coccurency?
                params = copy.deepcopy(server["parameter"])
                params["bbox"] = ",".join(map(str, bbox))

                counter_attempt += 1
                r = session.get(server["url"], params=params)
                if r.ok:
                    out_dir.mkdir(parents=True, exist_ok=True)
                    with open(out_file, 'wb') as out:
                        out.write(r.content)
                        counter_ok += 1

                input_queue.task_done()
            except queue.Empty:
                continue

    stat[id] = { "counter_total":   counter_total,
                 "counter_attempt": counter_attempt,
                 "counter_ok" :     counter_ok }

def fetch_tiles(server, tile_def_generator, output=pathlib.Path('.'), force=False):
    """
        fetch and store tiles

        @param server
                server definition object
        @param tile_def_generator
                generator of tile definitions consisting of [x, y, z, bbox] tuples
        @param output
                output folder path
        @param force
                flag to force to overwrite
    """

    input_queue = multiprocessing.JoinableQueue()
    stop_event = multiprocessing.Event()
    statistic = multiprocessing.Manager().dict()

    workers = []
    for i in range(server["concurrency"]):
        p = multiprocessing.Process(target=fetch_tile_worker,
                                    args=(i, input_queue, stop_event, server, output, force, statistic))
        workers.append(p)
        p.start()

    for [x, y, z, *bbox] in tile_def_generator:
        input_queue.put([x, y, z, bbox])

    input_queue.join()
    stop_event.set()
    for w in workers:
        w.join()

    def collect_result(s1, s2):
        if s1:
            return {
                "counter_total":   s1["counter_total"]   + s2["counter_total"],
                "counter_attempt": s1["counter_attempt"] + s2["counter_attempt"],
                "counter_ok":      s1["counter_ok"]      + s2["counter_ok"]
            }
        else:
            return s2

    result = reduce(collect_result, statistic.values(), None)
    print ("Total: {}, Ok: {}, Failed: {}, Skipped: {}".format(
            result["counter_total"],
            result["counter_ok"],
            result["counter_attempt"] - result["counter_ok"],
            result["counter_total"] - result["counter_attempt"]))
import argparse
import pathlib

def get_geo_tiles(server, output, force, tiles=None, zoom=None, bbox=None, geojson=None):
    server = None
    with server as f:
        server = json.load(f)

    if tile:
        fetch_tiles(server, generate_tile_def_from_list(tile), output, force);
    elif zoom:
        if server["parameter"]["srs"] == "EPSG:3857":
            projected = "mercator"
        elif server["parameter"]["srs"] == "EPSG:4326":
            projected = "geographic"
        else:
            raise argparse.ArgumentTypeError('Only EPSG:3857 and EPSG:4326 are supported.')
        if geojson:
            fetch_tiles(server, generate_tile_def_from_area(geojson, zoom, projected), output, force)
        elif bbox:
            fetch_tiles(server, generate_tile_def_from_bbox(bbox, zoom, projected), output, force)
    else:
        raise argparse.ArgumentTypeError('No explcit tile (-t) or area (-z. -b, -g) is defined')
