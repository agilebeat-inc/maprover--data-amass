# functions handling processing of queries and identifying tiles

import numpy as np
import pandas as pd
# geometry
import shapely.geometry as geom
# from shapely.ops import unary_union
from shapely.prepared import prep

from .utils import deg2num, num2deg, sample_complement
from .query_helpers import atomize_features

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
    # prep has methods: contains, contains_properly, covers, and intersects
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
        ix = np.random.choice(len(res),n_tile,replace = False)
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

def process_node(node_dict,tile_size):
    """
    if a map feature is really just a single node (ex. a water tower)
    then we just create a tile that is centered on that spot
    """
    pt = geom.Point(node_dict['lat'],node_dict['lon']).buffer(tile_size/2).envelope
    # to be consistent with other return types, return a tuple with (node,overlap)
    # but overlap is by definition 1 (or 0?) since a node doesn't have area
    return (pt,1)

def is_basically_closed(coords):
    """
    Heuristic to determine that the shape is 'basically' closed
    For some relations, a member with 'outer' role doesn't form a valid polygon
    """
    x0,y0 = coords[0]
    xN,yN = coords[-1]
    xRng = max(c[0] for c in coords) - min(c[0] for c in coords)
    yRng = max(c[1] for c in coords) - min(c[1] for c in coords)
    return abs(x0-xN) < 0.01*xRng and abs(y0-yN) < 0.01*yRng

def process_way(way_dict,**kwargs):
    """
    process an open or closed way, finding a (mutually disjoint) set of tiles
    that intersects the way.
    Args:
        way_dict: the geoJSON representation of the way
        **kwargs: forwarded to polygon_tiles, but with sensible defaults if not provided
    Returns:
        list of (Shapely.geometry.polygon.Polygon,float) tuples  (tile, overlap)
    """

    coords = [(x['lat'], x['lon']) for x in way_dict['geometry']]
    
    if len(coords) < 5: # treat it as node instead?
        return []
    is_closed = False
    if 'nodes' in way_dict:
        is_closed = way_dict['nodes'][0] == way_dict['nodes'][-1]
    elif 'role' in way_dict:
        is_closed = way_dict['role'] == 'outer' and is_basically_closed(coords)
    
    if is_closed:
        poly = geom.Polygon(shell = coords)
    else:
        LS = geom.LineString(coords)
        poly = way_to_poly(LS)
    # set default values which must be given to polygon_tiles function:
    kwargs.setdefault('n_tile',25)
    kwargs.setdefault('min_ovp',0.05)
    kwargs.setdefault('max_ovp',1)
    # default tile size should be based on zoom...
    kwargs.setdefault('tile_size',0.2 * approx_dim(poly))
    kwargs['poly'] = poly
    return polygon_tiles(**kwargs)

def process_relation(rel_dict,**kwargs):
    res = []
    for mem in rel_dict['members']:
        if mem['type'] == 'way':
            res.extend(process_way(mem,**kwargs))
        else: # node
            res.append(process_node(mem))
    return res

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
    Returns: the map coordinates as determined by .deg2num
    """
    if int(zoom) != zoom or zoom < 1 or zoom > 19:
        raise ValueError(f"zoom should be an integer in [1,19]; got {zoom}")
    center = list(tile.centroid.coords)[0]
    return (*deg2num(center[0],center[1],zoom),zoom)

def calc_map_locations(processed_query):
    """
    given a processed query (return value of process_query),
    and level of zooming, find the corresponding map coordinates to fetch the tiles
    Args:
        processed_query: the output of `process_query`
    Returns:
        a pandas.DataFrame with columns 'x', 'y', and 'z'
    """
    res = set()
    z = processed_query['zoom']
    for elem in processed_query['elements']:
        if not len(elem['tiles']): continue
        res.update(find_tile_coords(tile[0],z) for tile in elem['tiles'])
    return pd.DataFrame.from_records(list(res),columns = ['x','y','z'])

# this should become a method?
def process_query(
    ovp_query, zoom,max_tiles_per_entity = 25,
    min_ovp = 0, max_ovp = 1):
    """
    an Overpass API query returns a geoJSON-like response. This function loops over the response
    list and finds tiles which overlap with the query response. It appends the tiles
    to the query response, returning an augmented geoJSON object.
    Args:
        ovp_query: result of an Overpass API query
        zoom: level of zoooming in [1,19]
        max_tiles_per_entity: for ways or relations, max. # of tiles to retrive per element
        min_ovp: minimum intersection between tile and polygon to be included in the result
        max_ovp: maximum intersection between tile and polygon to be included in the result;
        set to anything < 1 if tiles on the interior of a polygon are not wanted
    Returns:
        a geoJSON-like object whose elements have an added 'tiles' property
    """
    for i,elem in enumerate(ovp_query['elements']):
        etype = elem['type']
        if etype == 'node':
            tiles = [process_node(elem,0.01)] # need to coordinate the size with zooming!
        elif etype == 'way':
            tiles = process_way(elem,n_tile = max_tiles_per_entity,
                min_ovp = min_ovp,max_ovp = max_ovp)
        elif etype == 'relation':
            tiles = process_relation(elem,min_ovp = 0.01)
        else:
            raise ValueError(f"Should not occur! type is {etype}")
        elem['tiles'] = tiles
    ovp_query['zoom'] = zoom # track @ which zoom it was processed
    ntiles = sum(len(e['tiles']) for e in ovp_query['elements'])
    ovp_query['total_tiles'] = ntiles
    print(f"Identified {ntiles} positive tiles at zoom {zoom}.")
    # this is obviously duplicative and should be reconsdiered
    # but for ease of inspection let's also add all the tiles
    # as a flat list, esp. to check min_ovp/max_ovp
    ovp_query['tiles'] = sum((e['tiles'] for e in ovp_query['elements']),[])
    return ovp_query

def create_tileset(geo_dict, zooms, buffer = 0):
    """
    This function creates outputs (x,y,z) tile coordinate files which can be
    fed into download_tiles.sh or the save_tiles function to get tiles from the OSM server.

    Args:
        geo_dict: an Overpass API query response
        zooms: zoom levels of tiles to be extracted 
        buffer: if nonzero, any negative tile will be at least this far away from the postive
        set, measured by L2 distance, ensuring more separation between classes if desired.
    
    Returns: dict with two pandas.DataFrame: 'positive' and 'negative'
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
    out_pos['latitude']  = [e[0] for e in LLpos]
    out_pos['longitude'] = [e[1] for e in LLpos]
    out_neg['latitude']  = [e[0] for e in LLneg]
    out_neg['longitude'] = [e[1] for e in LLneg]
    common_row = pd.merge(out_pos,out_neg,on = ['x','y','z']).shape[0]
    if common_row > 0:
        raise RuntimeError(f"Somehow there are {common_row} common rows!")
    return {'positive': out_pos, 'negative': out_neg }    
