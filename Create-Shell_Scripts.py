#!/usr/bin/env python
# coding: utf-8

import TileGenrator as TG
import random
import numpy as np
from shapely.ops import unary_union
from shapely.prepared import prep
import shapely.geometry as geom

def coord_xy(geojgeom):
    return [(x['lat'], x['lon']) for x in geojgeom]

def covering_grid(poly,tile_size):
    """
    create a grid of tiles which covers the input polygon
    Args:
        poly: a shapely.geometry.Polygon or MultiPolygon
        tile_size: (float) the dimension (width/height) of the tiles.
    Tile size is determined by the zoom level
    Returns: list of tiles - this is the initial filter; we still
    need to check agaist the actual polygon to see whether
    a given tile from the grid overlaps.
    """
    # prep only has contains, contains_properly, covers, and intersects
    # but that's fine since here we just use intersects
    bbox = poly.minimum_rotated_rectangle
    pbox = prep(bbox) 
    xL,yL,xR,yU = poly.bounds
    # numbers of horizontal and vertical tiles:
    nHoriz = np.ceil((xR - xL) / tile_size)
    nVert = np.ceil((yU - yL) / tile_size)
    tXX = np.arange(xL,xR,step = tile_size)
    tYY = np.arange(yL,yU,step = tile_size)
    boxes = []
    for i,x in enumerate(tXX):
        if i >= nHoriz-1: break
        nextX = tXX[i+1]
        for j,y in enumerate(tYY):
            if j >= nVert-1: continue
            nextY = tYY[j+1]
            tile_ij = geom.Polygon(
                shell = [(x,y),(nextX,y),(nextX,nextY),(x,nextY)]
            )
            # we already know it intersects envelope; second test:
            if pbox.intersects(tile_ij):
                boxes.append(tile_ij)
    
    return boxes # should make this a geopandas series?

def polygon_tiles(poly,tile_size,n_tile,min_ovp = 0.05,max_ovp = 1):
    """
    for the input polygon, return `n_tile` boxes (tile coordinates)
    that intersect with the polygon. 
    Args:
        poly: a shapely.geometry.polygon.Polygon
        tile_size: dimension of the tiles
        n_tile: number of tiles desired (set to np.Inf or something large for no bound)
        min_ovp: minimum overlap between a tile and polygon as a proportion of tile area
        max_ovp: maximum overlap between a tile and polygon as a proportion of tile area
    """
    candidates = covering_grid(poly,tile_size)
    tile_area = candidates[0].area
    min_area, max_area = tile_area * min_ovp, tile_area * max_ovp
    res = []
    
    for c in candidates:
        ovp = c.intersection(poly).area
        if ovp >= min_area and ovp <= max_area:
            res.append((c,ovp))
    if len(res) > n_tile:
        ix = random.sample(range(len(res)),n_tile)
        res = [res[i] for i in sorted(ix)]
    return res

def approx_dim(polyg):
    """
    calculate the 'approximate' dimension of a Polygon or LineString
    as the smaller of the sizes of the minimal bounding rectangle
    """
    def dist2d(p1,p2):
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    bx = list(polyg.minimum_rotated_rectangle.exterior.coords)
    d1,d2 = dist2d(bx[0],bx[1]), dist2d(bx[1],bx[2])
    return np.min([d1,d2])

def way_to_poly(way,buf_prop = 0.07):
    """
    for the input NOT closed way, return a fattened up version of the way
    which can be intersected with tiles 
    Args:
        way: a shapely.geometry.LineString
        buf_prop: amount by which to pad the 'way' into a 2d object
        this is calculated relative to the smaller dimension of the 
        'minimum rotated rectangle' that encloses the way
    Returns: a shapely.geometry.polygon.Polygon, for use in polygon_tiles
    """
    poly = way.buffer(distance = approx_dim(way) * buf_prop,resolution = 4)
    return poly

def process_way(way_dict,**kwargs):
    # way_dict = resp[1]; tile_size = 1e-4; n_tile = 50; min_ovp = 0.05; max_ovp = 1
    is_closed = way_dict['nodes'][0] == way_dict['nodes'][-1]
    coords = coord_xy(way_dict['geometry'])
    if is_closed:
        poly = geom.Polygon(shell = coords)
    else:
        LS = geom.LineString(coords)
        poly = way_to_poly(LS)
    print(f"The type of poly is {type(poly)}")
    # set default values which must be given to polygon_tiles function:
    kwargs.setdefault('n_tile',25)
    kwargs.setdefault('min_ovp',0.05)
    kwargs.setdefault('max_ovp',1)
    kwargs.setdefault('tile_size',0.2 * approx_dim(poly))
    kwargs['poly'] = poly
    return polygon_tiles(**kwargs)

def process_node(node_dict,tile_size):
    """
    if a map feature is really just a single node (ex. a water tower)
    then we just create a tile that is centered on that spot
    """
    pt = geom.Point(coord_xy(node_dict['geometry'])).buffer(tile_size/2).envelope
    # to be consistent with other return types, return a tuple with (node,overlap)
    # but overlap is by definition 1 since a node doesn't have area
    return (pt,1)

def process_relation(rel_dict,tile_size):
    raise NotImplementedError("we must implement the relations!")

def tile2json(tile):
    """
    Having found a set of overlapping tiles,
    turn them into a geoJSON representation
    Args: tile a shapely box
    Returns: a dict with basic geoJSON field that can be serialized
    into a geoJSON string. Note that the coords list has the first/last
    point listed twice since it is a 'closed way', conceptually
    """
    jsn = {}
    bb = tile.bounds
    jsn['bounds'] = {
        'minlat': bb[0],'minlon': bb[1],'maxlat': bb[2],'maxlon': bb[3]
    }
    jsn['geometry'] = [{'lat': x,'lon':y} for x,y in tile.exterior.coords]
    return jsn

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

def process_query(ovp_query,zoom):
    """
    an Overpass API query returns a geoJSON response. This function loops over the response
    list and finds tiles which overlap with the query response. It appends the tiles
    to the query response, returning an augmented geoJSON object.
    Args:
        ovp_query: result of an Overpass API query
    Returns:
        a geoJSON object whose elemnts have a 'tiles' property
    """
    elems = ovp_query['elements']
    ways = [e for e in elems if e['type'] == 'way']
    nodes = [e for e in elems if e['type'] == 'node']
    relations = [e for e in elems if e['type'] == 'relation']
    for elem in nodes:
        tile = process_node(elem,0.01) # need to coordinate the size with zooming!
        elem['tiles'] = [tile]
        elem['json_tiles'] = [tile2json(tile[0])]
    for elem in ways:
        tiles = process_way(elem)
        elem['tiles'] = tiles
        elem['json_tiles'] = [tile2json(t[0]) for t in tiles]
    for elem in relations:
        tiles = process_relation(elem,0.01)
        elem['tiles'] = tiles
        elem['json_tiles'] = [tile2json(t[0]) for t in tiles]
    new_elems = nodes + ways + relations
    ovp_query['elements'] = new_elems
    return ovp_query

def calc_map_locations(processed_query,zoom):
    """
    given a processed query (return value of process_query),
    and level of zooming, find the corresponding map coordinates to fetch the tiles
    """
    res = ()
    for elem in processed_query['elements']:
        res.update(find_tile_coords(tile,zoom) for tile in elem['tiles'])
    return list(res)

def sh_creator(geojson, zooms, file_path):

    """
    Create a shell script to download map tiles as .png files
    Args:
        ** geojson ** a geojson object (basically a JSON object with geometry->coordinates field)
        **zooms** - a list of integer between 1 ~ 19
        **file_path** - name of output file
        returns: None; call for the side effect of creating the shell script
    """
    if type(zooms) is int: zooms = [zooms]
    zooms = sorted(list(set(int(z) for z in zooms)))
    if any(zooms < 1 or zooms > 19):
        raise ValueError("zoom must be between 1 and 19 (inclusive)")

    features = geojson['elements']
    points_list = [f["geometry"]["coordinates"] for f in features]
    xyz = list(set([TG.deg2num(p[0],p[1],z) for p in points_list for z in zooms]))

    urls = [f"https://{random.choice('abc')}.tile.openstreetmap.org/{pt[2]}/{pt[0]}/{pt[1]}.png" for pt in xyz]

    with open(file_path,'w') as fh:
        def fprint(x):
            print(x,end = '\n',file = fh)

        fprint("#!/bin/bash")
    
        for i, u in enumerate(urls):
            zC, xC, yC = u.split('/')[-3:] # we only need last 3 elems
            lat, lon = TG.num2deg(int(xC), int(yC[:-4]), int(zC) )
            fprint(f"wget -O {zC}_{xC}_{yC} {u} #Lat: {lat}, Lon: {lon}")
            if i % 50 == 0:
                fprint('sleep 1.1')

if __name__ == "__main__":

    # example:
    import os
    if os.getcwd().startswith("/tmp/"):
        os.chdir("/mnt/c/Users/skm/Dropbox/AgileBeat")
    
    import tile_funcs as TF
    # testing:
    CN_mil = TF.TileCollection(place = "Beijing, China", buffer_size = 200000, 
        tag = 'military', values = ['airfield'])
    # bnd = CN_mil.boundaries(80000) # two corners defining a boundary box

    CN_mil.run_query() # gets results from overpass and stores in 'response' field

    resp = CN_mil.response['elements'] # a list of dicts

    pw = process_way(resp[1],max_ovp = 0.8)
    unary_union([p[0] for p in pw])