#!/usr/bin/env python3
# coding: utf-8

import random
import os, sys, json
from time import sleep
from pathlib import Path
import requests as rq

import numpy as np
import pandas as pd

# the other pieces we need to run queries and get tiles 
from .utils import deg2num, num2deg, sample_complement
from .query_processing import process_query, find_tile_coords, calc_map_locations
from .query_helpers import atomize_features


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
    UA = "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/77.0"
    tile_url = f"https://{random.choice('abc')}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    # cmd = f"wget --user-agent='please download' -O {fpath} {url}"
    if os.path.exists(fpath):
        print(f"Already have tile {fpath}!")
        return 0
    if os.path.isdir(fpath):
        raise ValueError(f"requested path {fpath} exists and is a directory!")
    try:
        res = rq.get(
            url=tile_url,
            headers={'User-Agent': UA}
        )
        status = res.status_code
        if status == 200:
            with open(fpath,'wb') as of:
                of.write(res.content)
            return 0
        else:
            print(f"Error: response {status} from server:\n{res.reason}")
            return status
    except Exception as e:
        print(f"Error getting tile: {e}")
        return 1

def save_tiles(df,output_dir,namefunc = None):
    """
    Save the tiles whose coordinates are in the input DataFrame,
    defined by columns x, y, and z
    Args:
        df: pandas.DataFrame (created by `create_tileset` function)
        output_dir: directory where the .png files should be stored
        namefunc: optional, a function that takes arguments x,y,z and returns a file name.
        The default name function is: `f'{z}_{x}_{y}.png'` for integers x,y,z.
    Returns:
        a pandas DataFrame reflecting the tiles which were actually downloaded, adding a column
        `file_loc` identifying where on the file system the tile .png was saved
    """
    if not isinstance(df,pd.core.frame.DataFrame):
        raise TypeError("df must be a pandas DataFrame!")
    if any(e not in df.columns for e in ('z','x','y')):
        raise ValueError("df must have columns x, y, and z")
    if namefunc is None:
        def namefunc(x,y,z):
            return f'{z}_{x}_{y}.png'

    opath = os.path.abspath(os.path.expanduser(output_dir))
    Path(opath).mkdir(parents=True, exist_ok=True)
    L = df.shape[0]
    flocs = [''] * L
    for i,xyz in enumerate(zip(df['x'],df['y'],df['z'])):
        x,y,z = xyz
        print(f"({i+1} of {L})...")
        sleep(0.75)
        outloc = os.path.join(opath,namefunc(x,y,z))
        if save_tile(x,y,z,outloc) == 0:
            flocs[i] = outloc
    df = df.assign(file_loc = flocs)
    return df[df['file_loc'] != '']

def add_latlon(df):
    """ add latitude/longitude values to a dataframe """
    LLs = [num2deg(x,y,z) for x,y,z in zip(df['x'],df['y'],df['z'])]
    LLdf = pd.DataFrame.from_records(LLs,columns = ['latitude','longitude'])
    return pd.concat([df.reset_index(drop=True),LLdf],axis = 1)

def basic_tileset(geo_dict, zooms, buffer = 0,n_neg = None):
    """
    This function creates outputs (x,y,z) tile coordinate files which can be
    fed into download_tiles.sh or the save_tiles function to get tiles from the OSM server.

    Args:
        geo_dict: an Overpass API query response
        zooms: zoom levels of tiles to be extracted 
        buffer: if nonzero, any negative tile will be at least this far away from the postive
        set, measured by L2 distance, ensuring more separation between classes if desired.
        n_neg: if provided, will fetch this many negative tiles rather than the 
    
    Returns: dict with two pandas.DataFrame: 'positive' and 'negative'
    """
    if not len(geo_dict['elements']):
        raise ValueError("The query is empty - cannot continue!")
    if type(zooms) is int:
        zooms = [zooms]
    if any(z < 2 or z > 19 for z in zooms):
        raise ValueError("all zoom levels must be between 2 and 19")
    
    nodes = atomize_features(geo_dict)
    points_list = [(node['lat'],node['lon']) for node in nodes]
    pos_DFs, neg_DFs = [], []

    for zoom in zooms:

        zxy = [(zoom,*deg2num(x,y,zoom)) for x,y in points_list]
        pos_df = pd.DataFrame.from_records(zxy,columns = ['z','x','y'])\
            .drop_duplicates(subset = ['x','y'])
        num_neg = pos_df.shape[0] if n_neg is None else int(n_neg)
        neg_x, neg_y = sample_complement(pos_df['x'],pos_df['y'],num_neg,buffer)
        neg_df = pd.DataFrame({'z': zoom,'x': neg_x,'y': neg_y}).sort_values(by = ['z','x','y'])
        pos_DFs.append(pos_df)
        neg_DFs.append(neg_df)
    
    out_pos = add_latlon(pd.concat(pos_DFs,axis = 0))
    out_neg = add_latlon(pd.concat(neg_DFs,axis = 0))

    common_row = pd.merge(out_pos,out_neg,on = ['z','x','y']).shape[0]
    if common_row > 0:
        raise RuntimeError(f"Somehow there are {common_row} common rows!")
    return {'positive': out_pos, 'negative': out_neg }    

def shapely_tileset(processed_query,min_ovp = 0,max_ovp = 1,
    n_neg = None,buffer = 0):
    """
    Create a DataFrame containing information on all tiles identified
    as downloadable
    Args:
        processed_query: return value of `process_query`
        min_ovp: float in [0,1]; only keep tiles where intersection between shape and tile box is at least `min_ovp`
        max_ovp: float in [0,1]; only keep tiles where intersection between shape and tile box is at most `max_ovp`
        n_neg: int, optional; number of negative tiles to download
        buffer: int, optional; margin between positive and negative data sets (in # of tiles)
    Returns:
        A pandas DataFrame with tile locations and corresponding metadata
    """
    types, xx, yy, qual, tags = [],[],[],[],[]
    z = processed_query['zoom']
    for elem in processed_query['elements']:
        for tile in elem['tiles']:
            qq = tile[1]
            if qq >= min_ovp and qq <= max_ovp:
                x,y,_ = find_tile_coords(tile[0],z)
                xx.append(x)
                yy.append(y)
                qual.append(tile[1])
                tags.append(json.dumps(elem['tags']))
                types.append(elem['type'])
    
    pos_df = pd.DataFrame({
        'z': z, 'x' : xx, 'y': yy, 
        'entity': types,
        'overlap': qual,'tags': tags,
        'placename': processed_query['query_info']['placename']
    }) \
    .drop_duplicates(subset = ['x','y']) \
    .sort_values(by = ['x','y'])
    if n_neg is None: n_neg = pos_df.shape[0]
    negt = sample_complement(pos_df['x'],pos_df['y'],n_neg,buffer)
    neg_df = pd.DataFrame({'z': z,'x': negt[0],'y': negt[1]}) \
        .sort_values(by = ['x','y'])
    return { 
        'positive': add_latlon(pos_df),
        'negative': add_latlon(neg_df)
    }
