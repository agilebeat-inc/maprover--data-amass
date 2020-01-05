#!/usr/bin/env python3
# coding: utf-8

import random
import os, sys
import subprocess as sp
import json
from time import sleep

import numpy as np
import pandas as pd

# the other pieces we need to run queries and get tiles
from .utils import deg2num, num2deg
from .query_processing import process_query
from .query_helpers import atomize_features

def sh_creator(geo_dict, zooms, positive_file_name, negative_file_name, buffer = 0):
    """
    This function creates outputs (x,y,z) tile coordinate files which can be
    fed into download_tiles.sh in order to get tiles from the OSM server.

    Args:
        geo_dict: an Overpass API query response
        zooms: zoom levels of tiles to be extracted 
        positive_file_name: file name with path for positive dataset
        negative_file_name: file name with path for negative dataset
        buffer: if nonzero, any negative tile will be at least this far away from the postive
        set, measured by L2 distance, ensuring more separation between classes if desired.
    
    Returns: None, called for the side-effect of creating the files `positive_file_name` and `negative_file_name`.
    """

    if type(zooms) is int:
        zooms = [zooms]
    if any(z < 2 or z > 19 for z in zooms):
        raise ValueError("all zoom levels must be between 2 and 19")
    
    nodes = atomize_features(geo_dict)
    points_list = [(node['lat'],node['lon']) for node in nodes]
    pos_DFs, neg_DFs = [], []

    for zoom in zooms:   

        xy = [deg2num(x,y,zoom) for x,y in points_list]

        pos_df = pd.DataFrame.from_records(xy,columns = ['x','y']).drop_duplicates()
        x_min, x_max, y_min, y_max = min(pos_df['x']), max(pos_df['x']), min(pos_df['y']), max(pos_df['y'])
        xrng, yrng = range(x_min, x_max+1), range(y_min,y_max+1)

        # get an equal number of 'negative' points which are in the bounding box
        n_pos = pos_df.shape[0]
        n_in_box = len(xrng) * len(yrng)
        # edge case - we sampled a solid rectangle of tiles
        if n_pos == n_in_box:
            raise ValueError("sh_creator: positives-only data set!")
        if 2 * n_pos > n_in_box:
            n_neg = n_in_box - n_pos
        else:
            n_neg = n_pos
        
        pos_xy = set((x,y) for x,y in zip(pos_df['x'],pos_df['y']))
        XY = np.array(list(pos_xy))

        def min_dist(x,y):
            dd = np.sum(np.square(XY - (x,y)),axis = 1)
            return np.sqrt(min(dd))

        neg_xy = set()
        while len(neg_xy) < n_neg:
            newx,newy = random.sample(xrng,n_neg), random.sample(yrng,n_neg)
            nearest_d = [min_dist(x,y) for x,y in zip(newx,newy)]
            if buffer >= 1:
                neg_xy.update((x,y) for x,y,d in zip(newx,newy,nearest_d) if d > buffer)
            else:
                neg_xy.update((x,y) for x,y in zip(newx,newy) if (x,y) not in pos_xy)
        
        neg_df = pd.DataFrame.from_records(list(neg_xy),columns = ['x','y'])\
            .head(n_neg)\
            .sort_values(by = ['x','y'])
        pos_df['z'] = zoom
        neg_df['z'] = zoom
        pos_DFs.append(pos_df)
        neg_DFs.append(neg_df)
    
    out_pos = pd.concat(pos_DFs,axis = 0)
    out_neg = pd.concat(neg_DFs,axis = 0)
    common_row = pd.merge(out_pos,out_neg,on = ['x','y','z']).shape[0]
    if common_row > 0:
        raise RuntimeError(f"Somehow there are {common_row} common rows!")
    print(f"Writing {out_pos.shape[0]} positive and {out_neg.shape[0]} negative samples")
    out_pos.to_csv(path_or_buf = positive_file_name,sep = '\t',header = False,index = False)
    out_neg.to_csv(path_or_buf = negative_file_name,sep = '\t',header = False,index = False)

def shell_permission(sh_file_name):
    """
    This function gives permission to created shell scripts
    - sh_file_name: a string. List of .sh file names separated by space
    """
    temp = subprocess.Popen(["chmod", "755", sh_file_name], stdout = subprocess.PIPE)
    data = subprocess.Popen(["ls", '-l', sh_file_name], stdout = subprocess.PIPE) 

def find_tile_coords(tile,zoom : int):
    """
    given a tile identified as 'of interest',
    get the map coordinates based on the centroid
    Args:
        tile: a shapely Polygon (should be a box as returned from process_node, process_way)
        whose vertices are latitude/longitude coordinates
        zoom: level of zoom between 1 and 19
    Returns: the map coordinates as determined by .deg2num
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

def save_tile(x,y,z,fpath):
    """
    Given the tile location (x,y) and zoom level z,
    fetch the corresponding tile from the server and save it
    to the location specfied in fpath.
    Note, this saves just one tile; usually, want to use `positive_dataset` instead.
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
            return f'lat_{y}_lon_{x}_zoom_{z}.png'
    if out_dir.endswith('/'): out_dir = out_dir[:-1]
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
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

def negative_dataset(processed_query,out_dir,namefunc = None):
    return

if __name__ == "__main__":

    # TODO: 
    # determine tile size from input zoom level
    # unit testing?
    # negative dataset function
    from .query_helpers import run_ql_query

    # testing:
    ES_mil = run_ql_query(place = "Madrid, Spain", 
        buffersize = 200000, 
        tag = 'military', values = ['airfield','bunker'])

    # first approach: take any tile in which any query node appears
    # as a positive example, and any other tile in the bounding box
    # as a negative example:
    # should run the script 'download_tiles.sh' and input
    # the output file (for positive and negative respectively)
    os.chdir("/mnt/c/Users/skm/Dropbox/AgileBeat/pipeline-1")
    sh_creator(ES_mil,[17,18,19],'ES_testpos.tsv','ES_testneg.tsv',buffer = 10)

    # second approach: use Shapely to sample tiles that overlap
    # with the geometric object, specifying min/max overlap if desired
    qq = process_query(CN_mil,17)

    positive_dataset(qq,'/mnt/c/Users/skm/Documents/test_picz')
    # the URL composition is defined for tiles in
    # see https://wiki.openstreetmap.org/wiki/Tile_servers
    # spots = calc_map_locations(qq)
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