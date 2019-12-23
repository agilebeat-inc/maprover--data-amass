# functions handling processing of queries and identifying tiles

import numpy as np
# geometry
import shapely.geometry as geom
from shapely.ops import unary_union
from shapely.prepared import prep


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
    # way_dict = rel[14]; kwargs = {}
    coords = coord_xy(way_dict['geometry'])
    if len(coords) < 5: # treat it as node instead?
        return []
    if 'nodes' in way_dict:
        is_closed = way_dict['nodes'][0] == way_dict['nodes'][-1]
    elif 'role' in way_dict:
        is_closed = way_dict['role'] == 'outer' and is_basically_closed(coords)
    else:
        is_closed = False
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

# rel = qq['elements'][8]['members']
# for i,rl in enumerate(rel):
#     print(f"Processing way# {i}")
#     ts = process_way(rl)

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

# this should become a method?
def process_query(ovp_query,zoom,max_tiles_per_entity = 25,min_ovp=0,max_ovp=1):
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
        a geoJSON object whose elements have an added 'tiles' property
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
    return ovp_query

if __name__ == '__main__':

    import os
    from collections import Counter
    if os.getcwd().startswith('/tmp/'):
        os.chdir("/mnt/c/Users/skm/Dropbox/AgileBeat/pipeline-1")
    from query_helpers import run_ql_query
    # test that ways and relations are correctly processed:
    # this query should return 8 ways and 2 relations
    qq = run_ql_query('San Juan, Puero Rico','landuse',['forest'],10000)
    rels = [e for e in qq['elements'] if e['type'] == 'relation']
    qp = process_query(qq,17)

    pw = process_way(qq['elements'][1],max_ovp = 0.8)
    unary_union([p[0] for p in pw])
    
