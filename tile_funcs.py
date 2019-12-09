#!/usr/bin/env python
# coding: utf-8

# ## OSMXTRACT

import json
from osmxtract import overpass, location
from collections import Counter
import shapely.geometry as geom
# geopandas provides vectorized versions of
# many shapely operations via its GeoSeries data type
# and some syntatic sugar for set operations
# e.g. - for set difference, & for intersection
# the overlay operation is basically what we want:
# overlay a tile grid with a certain set of polygons
# and get non-type examples with overlay (symmetric-difference)
# this can also be accomplished via a 'spatial join'
# import geopandas as gpd

class TileCollection:
    
    def __init__(self, place, buffer_size, tag, values):
        self.place = place
        self.buffer_size = buffer_size  #-- buffer size in (Km)
        self.tag = tag
        self.values = values            #-- values must be a list (e.g) ['runway', taxiway]
        self.response = None
     
    def boundaries(self,buf = None):
        """
        # Define area in lat/long where tiles are extracted
        """
        if buf is None: buf = self.buffer_size
        lat, lon = location.geocode(self.place)
        # Buffer size in meter(M) unit
        bound = location.from_buffer(lat, lon, buffer_size = buf)
        return bound

    def run_query(self):
        """
        Extracted featured tiles and save as a json file
        """
        query = overpass.ql_query(self.boundaries(), tag = self.tag, values = self.values)
        self.response = overpass.request(query)
    
    def way_to_nodes(self,way):
        LAT = [coordinate['lat'] for coordinate in way['geometry']]
        LON = [coordinate['lon'] for coordinate in way['geometry']]
        parsed_to_points = [{
            'type': 'node',
            'id': way['id'],
            'lat':point[0],
            'lon':point[1], 
            'tags': way['tags']} 
            for point in zip(LAT,LON)]
        return parsed_to_points
    
    # we want to defer untoward manipulation of ways and relations till we're matching
    # tiles against them.
    # def json_to_geojson(self):
        
    #     if self.response is None:
    #         self.run_query()
        
    #     features_to_points = []
    #     data = self.reponse
        
    #     for elem in data['elements']: 
    #         if elem['type'] == 'node':
    #             features_to_points.append(elem)
        
    #         elif elem['type'] == 'way':
    #             features_to_points.append(self.way_to_nodes(elem))
        
    #         else:
    #             features_to_points += [self.way_to_nodes(member) for member in elem['members']]

    #     feature_collection = [overpass.as_geojson(f, 'point') for f in features_to_points]
    #     return feature_collection

if __name__ == '__main__':

    CN_mil = TileCollection(place = "Beijing, China", buffer_size = 200000, 
        tag = 'military', values = ['airfield'])
    bnd = CN_mil.boundaries(80000) # two corners defining a boundary box

    CN_mil.run_query() # actually do the thing?

    resp = CN_mil.response['elements'] # a list of dicts
    # each element is a geoJSON object. we want to append to the info here
    # the set of overlapping tiles.

    Counter(e['type'] for e in resp) # all ways
    [len(e['nodes']) for e in resp]
    nodeHT = [(e['nodes'][0],e['nodes'][-1]) for e in resp]
    # is_closed = [a == b for a,b in nodeHT]

    # any closed ways get turned into polygons:
    # res = []
    # for e in resp:
    #     typ = e['type']
    #     gm = e['geometry']
    #     if typ == 'node':
    #         res.append(geom.Point(gm[0]['lat'],gm[0]['lon']))
    #     elif typ == 'way':
    #         is_closed = e['nodes'][0] == e['nodes'][-1]
    #         if is_closed:
    #             res.append(geom.Polygon(coord_xy(gm)))
    #         else:
    #             res.append(geom.LineString(coord_xy(gm)))
    #     elif typ == 'relation':
    #         pass # figure this out later!
    #     else:
    #         raise ValueError(f"unknown type {typ}! RUn away!")

    # json_blob = CN_mil.json_to_geojson('airfield_Bejing')
    
    # the Overpass API response is already in geoJSON
    with open('foo.txt','w') as fh:
        json.dumps(resp)
