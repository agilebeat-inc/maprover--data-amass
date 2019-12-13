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
        Define area in lat/long where tiles are extracted
        Args: buf (optional, defaults to self.buffer_size)
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
    
def run_ql_query(place,buffersize,tag,values,case = False,timeout = 25):
    """
    Run an overpass API query

    Args:
        place: either a location such as "Tuscaloosa, AL", 91210 
        or a (latitiude,longitude) tuple
        buffersize: size, in meters, 

    """
    # Determine the bounding box
    if type(place) in (str,int):
        lat, lon = location.geocode(place)
    elif type(place) in (list,tuple):
        lat, lon = [float(place[0]),float(place[1])]
    else:
        raise ValueError("'place' should be a string, integer, or length-2 list")
    bounds = location.from_buffer(lat, lon, buffer_size = buffersize)
    query = overpass.ql_query(bounds, tag, values,case,timeout)
    return overpass.request(query)

if __name__ == '__main__':

    CN_mil = run_ql_query(place = "Beijing, China", buffersize = 200000, 
        tag = 'military', values = ['airfield'])


