#!/usr/bin/env python
# coding: utf-8

import TileCollection as TC
import TileGenerator as TG

import math
import random
import subprocess
import os
import pandas as pd



def featured_tiles(place, buffer_size, tag, values):
    """
    Run an osm query, returning a geojson file
       - place: geocode. (e.g. 'Beijing, China')
       - buffer_size: radius centered place in kilometer
       - tag: openstreet map feature tag
       - values: openstreet map feature values
       - file_name: file name saved as geojson
    """
    boundaries = TC.boundaries(place = place, buffer_size = buffer_size)
    return TC.map_features_json_response(bounds = boundaries, tag=tag, values=values)


def sh_creator(gj, zooms, positive_file_name, negative_file_name):
    """
    The function creates shell scripts to collect featured and non-featured tiles 
    using geojson output.
    - gj: geojson object as returned by featured_tiles
    - zooms: zoom levels of tiles to be extracted 
    - positive_file_name: file name with path for positive dataset
    - negative_file_name: file name with path for negative dataset
    """
    features = gj['elements']
    if type(zooms) is int:
        zooms = [zooms]
    if any(z < 2 or z > 19 for z in zooms):
        raise ValueError("all zoom levels must be between 2 and 19")
    
    for zoom in zooms:   

        points_list = [f["geometry"]["coordinates"] for f in features]

        xy = [TG.deg2num(x,y,zoom) for x,y in points_list]

        pos_df = pd.DataFrame.from_records(xy,columns = ['x','y']).drop_duplicates()
        x_min, x_max, y_min, y_max = min(pos_df['x']), max(pos_df['x']), min(pos_df['y']), max(pos_df['y'])
        xrng, yrng = range(x_min, x_max+1), range(y_min,y_max+1)

        # get an equal number of 'negative' points which are in the bounding box
        n_pos = pos_df.shape[0]
        n_in_box = (x_max - x_min + 1) * (y_max - y_min + 1)
        if 2 * n_pos > n_in_box:
            n_neg = n_in_box - n_pos
        else:
            n_neg = n_pos
        
        neg_xy = set()
        neg_xy.update((x,y) for x,y in zip(random.sample(xrng,n_neg), random.sample(yrng,n_neg)))
        while len(neg_xy) < n_neg:
            neg_xy.update((x,y) for x,y in zip(random.sample(xrng,n_neg), random.sample(yrng,n_neg)))
        
        neg_df = pd.DataFrame.from_records(neg_xy,columns = ['x','y']).head(n_neg)
        pos_df['z'] = zoom
        neg_df['z'] = zoom
        pos_df.to_csv(path_or_buf = positive_file_name,sep = '\t',header = False,index = False)
        neg_df.to_csv(path_or_buf = negative_file_name,sep = '\t',header = False,index = False)


def shell_permission(sh_file_name):
    """
    This function gives permission to created shell scripts
    - sh_file_name: a string. List of .sh file names separated by space
    """
    temp = subprocess.Popen(["chmod", "755", sh_file_name], stdout = subprocess.PIPE)
    data = subprocess.Popen(["ls", '-l', sh_file_name], stdout = subprocess.PIPE) 
    # subprocess.check_call([sh_file_name, "bash"])                

if __name__ == '__main__':

    tags_of_interest = ['airfield', 'bunker','barracks', 'checkpoint', 'danger_area', 'naval_base', 'nuclear_explosion_site']
    GJ = featured_tiles(place="Beijing, China", buffer_size=500000, 
        tag='military', values = tags_of_interest)

    # ## 2. Using .geogson, create shell script for featured and non-featured classes

    sh_creator(GJ, zooms=[17,18], positive_file_name = 'mil_Beijing_pos.tsv', 
        negative_file_name ='mil_Beijing_neg.tsv')


    # ## 3. Give permission to created shell scripts

    # shell_permission('mil_Beijing_pos.sh non-mil_Beijing_neg.sh')



