#!/usr/bin/env python3
# coding: utf-8

import random
import os, sys
import subprocess as sp
import json
from time import sleep
from pathlib import Path

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
    url = f"https://{random.choice('abc')}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    cmd = f"wget -O {fpath} {url}"
    if os.path.exists(fpath):
        print(f"Already have tile {fpath}!")
        return 0
    try:
        res = sp.run(cmd,shell = True,stdout = sp.PIPE,stderr = sp.STDOUT)
        return 0
    except Exception as e:
        print(f"Error getting tile: {e}")
        return 1

def save_tiles(df,output_dir):
    """
    Save the tiles whose coordinates are in the input DataFrame,
    defined by columns x, y, and z
    Args:
        df: pandas.DataFrame (created by `create_tileset` function)
        output_dir: directory where the .png files should be stored
    Returns:
        None, called for side-effect of downloading tiles
    """
    if not isinstance(df,pd.core.frame.DataFrame):
        raise TypeError("df must be a pandas DataFrame!")
    if any(e not in df.columns for e in ('x','y','z')):
        raise ValueError("df must have columns x, y, and z")
    if output_dir.endswith('/'): output_dir = output_dir[:-1]
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    i, L = 0, df.shape[0]
    for x,y,z in zip(df['x'],df['y'],df['z']):
        i += 1
        print(f"({i} of {L})...")
        if i % 50 is 0:
            print('zzz')
            sleep(1.33)
        tile_name = f"{x}_{y}_{z}.png"
        outloc = output_dir + '/' + tile_name
        save_tile(x,y,z,outloc)

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
    file_locs, types, xx, yy, qual, tags = [],[],[],[],[],[]
    if namefunc is None:
        def namefunc(x,y,z):
            return f'lat_{y}_lon_{x}_zoom_{z}.png'

    if out_dir.endswith('/'): out_dir = out_dir[:-1]
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    
    z = processed_query['zoom']
    
    for elem in processed_query['elements']:
        tagstr = json.dumps(elem['tags'])
        entity = elem['type'] # node, way, or relation
        for tile in elem['tiles']:
            if random.random() < 0.08: sleep(0.67)
            x,y,_ = find_tile_coords(tile[0],z)
            floc = f"{out_dir}/{namefunc(x,y,z)}"
            # first check whether we already got this tile
            # for example densely packed nodes will have a lot
            # of closely overlapping tiles
            got_png = save_tile(x,y,z,floc)
            if got_png is 0:
                xx.append(x)
                yy.append(y)
                qual.append(tile[1])
                tags.append(tagstr)
                types.append(entity)
                file_locs.append(floc)
    print(f'Got {len(xx)} records!')
    return pd.DataFrame({
        'lat' : xx, 'lon': yy, 'z': z,
        'location': file_locs, 'entity': types,
        'overlap': qual,'tags': tags,
        'placename': processed_query['query_info']['placename']
    })

def negative_dataset(processed_query,out_dir,buffer = 0,namefunc = None):
    
    processed_query = qp
    buffer = 5
    xyz = calc_map_locations(processed_query)
    # now use sample_complement to ID negative tiles:
    n_pos = xyz.shape[0]
    # it is possible that we select tiles within a polygon here,
    # which is not desired. But using 'buffer' should make this very
    # unlikely
    negt = sample_complement(xyz['x'],xyz['y'],n_pos,buffer)
    negdf = pd.DataFrame(
        {'x': negt[0],'y': negt[1],'z': processed_query['zoom']}
    )
    # now save them (we do not need metadata beyond locations
    # since negatives by definition are unknown quantities)
    save_tiles(negdf,out_dir)
    return negdf

