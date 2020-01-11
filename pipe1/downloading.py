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
from .utils import deg2num, num2deg
from .query_processing import process_query
from .query_helpers import atomize_features

def sample_complement(xx,yy,n,buffer = 0):
    """ 
    Take a sample from the bounding box of the elements in xx and yy.
    The pairs [(x,y) for x,y in zip(xx,yy)] are not included in the sample;
    we are sampling from the complement of such elements.
    Args:
        xx: iterable of ints or other discrete elements
        yy: iterable of ints or other discrete elements
        n: number of items sampled from the complement of Cartesian product of xx and yy
        buffer: int; if positive, each element in the sample must be at least this far away
        from a 'positive' element
    Returns:
        tuple newx,newy which are lists of items of the same type as xx and yy
    Raises:
        ValueError for a few edge cases
    """

    n_pos = len(xx)
    if len(yy) != n_pos:
        msg = f"sample_complement: lengths of {xx} and {yy} must match!"
        raise ValueError(msg)
    x_min, x_max, y_min, y_max = min(xx), max(xx), min(yy), max(yy)
    xrng, yrng = range(x_min, x_max+1), range(y_min,y_max+1)

    # get an equal number of 'negative' points which are in the bounding box
    n_in_box = len(xrng) * len(yrng)
    print(f"{n_pos} positive tiles; {n_in_box} tiles in area")
    # edge case - we sampled a solid rectangle of tiles
    if n_pos >= n_in_box:
        msg = f"sh_creator: {n_pos} positive tiles and {n_in_box} total tiles!"
        raise ValueError(msg)
    n_neg = min(n_in_box - n_pos,n)
    
    pos_xy = set((x,y) for x,y in zip(xx,yy))
    XY = np.array(list(pos_xy))

    def min_dist(x,y):
        dd = np.sum(np.square(XY - (x,y)),axis = 1)
        return np.sqrt(min(dd))

    rng = np.random.default_rng()
    neg_xy = set()
    # if the buffer is large, there may not be enough tiles
    # but its not possible to calculate beforehand
    tries = 0 
    while len(neg_xy) < n_neg:
        tries += 1
        if tries > 5: break
        newx = rng.integers(x_min,x_max,n_neg,endpoint=True)
        newy = rng.integers(y_min,y_max,n_neg,endpoint=True)
        nearest_d = [min_dist(x,y) for x,y in zip(newx,newy)]
        if buffer >= 1:
            neg_xy.update((x,y) for x,y,d in zip(newx,newy,nearest_d) if d > buffer)
        else:
            neg_xy.update((x,y) for x,y in zip(newx,newy) if (x,y) not in pos_xy)
    neg_xy = list(neg_xy)[:n_neg]
    return [e[0] for e in neg_xy], [e[1] for e in neg_xy]

def create_tileset(geo_dict, zooms, buffer = 0):
    """
    This function creates outputs (x,y,z) tile coordinate files which can be
    fed into download_tiles.sh in order to get tiles from the OSM server.

    Args:
        geo_dict: an Overpass API query response
        zooms: zoom levels of tiles to be extracted 
        buffer: if nonzero, any negative tile will be at least this far away from the postive
        set, measured by L2 distance, ensuring more separation between classes if desired.
    
    Returns: dict with two items: 'positive' and 'negative'; both are pandas.DataFrame
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
        n_neg = pos_df.shape[0]
        neg_x, neg_y = sample_complement(pos_df['x'],pos_df['y'],n_neg,buffer)
        neg_df = pd.DataFrame({'x': neg_x,'y': neg_y}).sort_values(by = ['x','y'])
        pos_df['z'] = zoom
        neg_df['z'] = zoom
        pos_DFs.append(pos_df)
        neg_DFs.append(neg_df)
    
    out_pos = pd.concat(pos_DFs,axis = 0)
    out_neg = pd.concat(neg_DFs,axis = 0)
    # add back the longitude/latitude coordinates
    LLpos = [num2deg(x,y,z) for x,y,z in zip(out_pos['x'],out_pos['y'],out_pos['z'])]
    LLneg = [num2deg(x,y,z) for x,y,z in zip(out_neg['x'],out_neg['y'],out_neg['z'])]
    out_pos['latitude'] = [e[0] for e in LLpos]
    out_pos['longitude'] = [e[1] for e in LLpos]
    out_neg['latitude'] = [e[0] for e in LLneg]
    out_neg['longitude'] = [e[1] for e in LLneg]
    common_row = pd.merge(out_pos,out_neg,on = ['x','y','z']).shape[0]
    if common_row > 0:
        raise RuntimeError(f"Somehow there are {common_row} common rows!")
    return {'positive': out_pos, 'negative': out_neg }

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
        save_tile(x,y,z,output_dir + '/' + tile_name)

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
    raise NotImplementedError("It is not implemented!")

