import json
import overpass as ovp 
from osmxtract import overpass, location
import geopandas as gpd

#====================================================
# Extracted all tiles and save as a json file
#====================================================
def all_tiles(lat_1, long_1, lat_2, long_2):
    api = ovp.API(timeout=600)
    map_query = ovp.MapQuery(lat_1, long_1, lat_2, long_2)
    response = api.Get(map_query, responseformat="json")
    return response
     
#====================================================
# Define area in lat/long where tiles are extracted
#====================================================
def boundaries(place, buffer_size):     
    lat, lon = location.geocode(place)
    bound = location.from_buffer(lat, lon, buffer_size = buffer_size)  # Buffer size in meter(M) unit
    return bound

    
#====================================================
# Extracted featured tiles and save as a json file
#===================================================
def map_features_json_response(bounds, tag, values ): 
    query = overpass.ql_query(bounds = bounds, tag = tag, values = values)
    response = overpass.request(query)
    return response
    
    
#===================================================
# Save as a geojson file
#===================================================
def json_to_geojson(json_response):
    my_data = json_response['elements']            # -- response is json format 

    features_to_points = []
    for feature in my_data: 
        if 'tags' not in feature:
            feature['tags'] = 'Feature'
        else:
            pass

        if feature['type'] == 'node':                                # 'node' element
            features_to_points.append(feature)

        elif feature['type'] == 'way' :                              # 'way' element
            try:
                LAT = [coordinate['lat'] for coordinate in feature['geometry']]
                LON = [coordinate['lon'] for coordinate in feature['geometry']]

                parsed_to_points = [
                    {'type': 'node', 'id': feature['id'],
                     'lat': x, 'lon': y, 'tags': feature['tags']} for x,y in zip(LAT,LON)]
                features_to_points.extend(parsed_to_points)
            except:
                continue

        else:                                                             # 'relation' element
            index = feature['id']
            tag = feature['tags']
            for member in feature['members']:
                try:
                    LAT = [coordinate['lat'] for coordinate in member['geometry']]
                    LON = [coordinate['lon'] for coordinate in member['geometry']]

                    parsed_to_way_to_point = [
                        {'type': 'node', 'id': index, 'lat': x, 'lon': y, 
                         'tags': tag} for x,y in zip(LAT,LON)]
                    features_to_points.extend(parsed_to_way_to_point)
                except:
                    continue

    json_response['elements'] = features_to_points
    return ovp.as_geojson(json_response, 'point') 
    

