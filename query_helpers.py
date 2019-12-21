from osmxtract import overpass, location

def run_ql_query(place,tag,values,buffersize = None,case = False,timeout = 25):
    """
    Run an overpass API query

    Args:
        place: either a location such as "Tuscaloosa, AL", 91210 
        or a (latitiude,longitude) tuple, or a tuple of 4 numbers which will
        be considered to be the bounds (and in this case we ignore buffersize)
        buffersize: size, in meters
    Returns: JSON result of an Overpass API query, with some extra metadata 
        about the query appended.

    """
    # Determine the bounds
    if type(place) in (str,int):
        lat, lon = location.geocode(place)
    elif type(place) in (list,tuple) and len(place) is 2:
        lat, lon = float(place[0]), float(place[1])
    elif len(place) is 4 and all(e == float(e) for e in place):
        # get center for consistent return value information
        lat, lon = (place[2] - place[0])/2, (place[3] - place[1])/2
        buffersize = 0
    else:
        raise ValueError("run_ql_query: Incompatible input for 'place' parameter")
    
    if buffersize is None:
        raise ValueError(f"need a buffersize for this 'place' argument: {place}")
    if buffersize <= 0:
        bounds = place 
    else:
        bounds = location.from_buffer(lat, lon, buffer_size = buffersize)
    query = overpass.ql_query(bounds, tag, values,case,timeout)
    res = overpass.request(query)
    # append info about the query so it's automatically tracked
    res['query_info'] = {
        'query': query,
        'placename': place if type(place) in (str,int) else None,
        'geolocation': (lat,lon),
        'bounds': bounds
    }
    return res
    
def atomize_features(ovp_response):
    """
    if we want to turn a response into a bag of homogeneous nodes,
    this function will do it.
    Args: 
        ovp_response: an Overpass API response
    Returns:
    """

    def way_to_nodes(way):
        LAT = [coordinate['lat'] for coordinate in way['geometry']]
        LON = [coordinate['lon'] for coordinate in way['geometry']]
        return [{
            'type': 'node', 'id': way['id'],
            'lat':point[0], 'lon':point[1], 'tags': way['tags']
            } for point in zip(LAT,LON)]

    node_list = []
    for feature in ovp_response['elements']: 
        if 'tags' not in feature:
            feature['tags'] = 'empty'

        if feature['type'] == 'node':
            node_list.append(feature)

        elif feature['type'] == 'way':
            try:
                node_list.extend(way_to_nodes(feature))
            except:
                continue

        else:    # 'relation' element
            for member in feature['members']:
                try:
                    node_list.extend(way_to_nodes(member))
                except:
                    continue
    return node_list
    

if __name__ == '__main__':

    # example queries:
    q1 = run_ql_query(90210,'leisure',['park'],5000)
    qq_nodes = atomize_features(qq)

    CN_mil = run_ql_query(place = "Beijing, China", buffersize = 200000, 
        tag = 'military', values = ['airfield'])