#!/usr/bin/env python
# coding: utf-8

# standard modules
import random
import os, sys
import subprocess as sp
import json
from time import sleep

# math/data
import numpy as np
import pandas as pd

# hackery when using in vscode interactive
if os.getcwd().startswith('/tmp/'):
    sys.path.append("/mnt/c/Users/skm/Dropbox/AgileBeat/pipeline-1") 
# the other pieces we need to run queries and get tiles
from TileGenerator import deg2num, num2deg
from tile_funcs import run_ql_query
from processing import process_query

def find_tile_coords(tile,zoom : int):
    """
    given a tile identified as 'of interest',
    get the map coordinates based on the centroid
    Args:
        tile: a shapely Polygon (should be a box as returned from process_node, process_way)
        whose vertices are latitude/longitude coordinates
        zoom: level of zoom between 1 and 19
    Returns: the map coordinates as determined by TileGenerator.deg2num
    """
    if int(zoom) != zoom or zoom < 1 or zoom > 19:
        raise ValueError(f"zoom should be an integer in [1,19]; got {zoom}")
    center = list(tile.centroid.coords)[0]
    return deg2num(*center,zoom)

def calc_map_locations(processed_query):
    """
    given a processed query (return value of process_query),
    and level of zooming, find the corresponding map coordinates to fetch the tiles
    """
    res = set()
    z = processed_query['zoom']
    for elem in processed_query['elements']:
        res.update(find_tile_coords(tile[0],z) for tile in elem['tiles'])
    return list(res)

def save_file(x,y,z,fpath):
    """
    Given the tile location (x,y) and zoom level z,
    fetch the corresponding tile from the server and save it
    to the location specfied in fpath
    Args:
        x,y,z: integers
        fpath: str
    Returns: int, 0 if successful and 1 otherwise
    """
    url = f"https://{random.choice('abc')}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    # fix to run without shell=True - does it matter?
    # cmds = ["wget", f"-O {fpath}", f"{url}"]
    cmds = f"wget -O {fpath} {url}"
    try:
        res = sp.run(cmds,shell = True,stdout = sp.PIPE,stderr = sp.STDOUT)
        return 0
    except Error as e:
        print(f"Error getting tile: {e}")
        return 1

def positive_dataset(processed_query,out_dir,namefunc = None):
    """
    download the map tiles corresponding to the locations in
    the given query; save tiles along with a DataFrame of metadata
    to directory `out_dir`.
    Args:
        processed_query: return value of `process_query`
        out_dir: directory where files should be saved
        namefunc: function mapping tuple (x,y,z) into a file name
    """
    file_locs, types, xx, yy, qual, tags = ([],[],[],[],[],[])
    if namefunc is None:
        def namefunc(x,y,z):
            return f'lat_{x}_lon_{y}_zoom_{z}.png'
    if out_dir.endswith('/'): out_dir = out_dir[:-1]
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    Elems = processed_query['elements']
    z = processed_query['zoom']
    
    for elem in Elems:
        tagstr = json.dumps(elem['tags'])
        entity = elem['type'] # node, way, or relation
        for tile in elem['tiles']:
            if random.random() < 0.08: sleep(0.67)
            x,y = find_tile_coords(tile[0],z)
            floc = f"{out_dir}/{namefunc(x,y,z)}"
            # first check whether we already got this tile
            # for example densely packed nodes will have a lot
            # of closely overlapping tiles
            if os.path.exists(floc): continue
            got_png = save_file(x,y,z,floc)
            if got_png is 0:
                xx.append(x)
                yy.append(y)
                qual.append(tile[1])
                tags.append(tagstr)
                types.append(entity)
                file_locs.append(floc)
    df = pd.DataFrame({
        'lat' : xx, 'lon': yy, 'z': z,
        'location': file_locs, 'entity': types,
        'overlap': qual,'tags': tags,
        'placename': processed_query['query_info']['placename']
    })
    print(f'Got {len(xx)} records!')
    #TODO: append to existing if there's already data?
    df.to_csv(path_or_buf = f'{out_dir}/pos_metadata.csv',index = False)

if __name__ == "__main__":

    # TODO: determine tile size from input zoom level
    # writing unit tests
    # process_relation function
    # create a class to structure all the functions?

    # testing:
    CN_mil = run_ql_query(place = "Madrid, Spain", 
        buffersize = 200000, 
        tag = 'military', values = ['airfield','bunker'])

    resp = CN_mil['elements'] # what gets processed by other funcs
    pw = process_way(resp[1],max_ovp = 0.8)
    unary_union([p[0] for p in pw])

    qq = process_query(CN_mil,17)
    spots = calc_map_locations(qq)

    positive_dataset(qq,'/mnt/c/Users/skm/Documents/test_picz')
    # the URL composition is defined for tiles in
    # see https://wiki.openstreetmap.org/wiki/Tile_servers
    # out_dir = "/mnt/c/Users/skm/Dropbox/AgileBeat"
    # for x,y in spots:
    #     outF = f"{out_dir}/lat_{x}_lon_{y}_zoom_{z}.png"
    #     save_file(x,y,15,outF)
    #     print(f"Got file {outF}")
    
    # whatever header is sent by default is not responded to
    # this or using subprocess and wget or curl works
    # import requests as rq
    # headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5)\
    #         AppleWebKit/537.36 (KHTML, like Gecko) Cafari/537.36'}
    # res = rq.get(url,headers = headers)
    # print(res.status_code)
    # with open("/mnt/c/Users/skm/Dropbox/AgileBeat/test.png",'wb') as fh:
    #     fh.write(res.content)

# defunct
# def sh_creator(geojson, zooms, file_path):

#     """
#     Create a shell script to download map tiles as .png files
#     Args:
#         ** geojson ** a geojson object (basically a JSON object with geometry->coordinates field)
#         **zooms** - a list of integer between 1 ~ 19
#         **file_path** - name of output file
#         returns: None; call for the side effect of creating the shell script
#     """
#     if type(zooms) is int: zooms = [zooms]
#     zooms = sorted(list(set(int(z) for z in zooms)))
#     if any(zooms < 1 or zooms > 19):
#         raise ValueError("zoom must be between 1 and 19 (inclusive)")

#     features = geojson['elements']
#     points_list = [f["geometry"]["coordinates"] for f in features]
#     xyz = list(set([TG.deg2num(p[0],p[1],z) for p in points_list for z in zooms]))

#     urls = [f"https://{random.choice('abc')}.tile.openstreetmap.org/{pt[2]}/{pt[0]}/{pt[1]}.png" for pt in xyz]

#     with open(file_path,'w') as fh:
#         def fprint(x):
#             print(x,end = '\n',file = fh)

#         fprint("#!/bin/bash")
    
#         for i, u in enumerate(urls):
#             zC, xC, yC = u.split('/')[-3:] # we only need last 3 elems
#             lat, lon = TG.num2deg(int(xC), int(yC[:-4]), int(zC) )
#             fprint(f"wget -O {zC}_{xC}_{yC} {u} #Lat: {lat}, Lon: {lon}")
#             if i % 50 == 0:
#                 fprint('sleep 1.1')