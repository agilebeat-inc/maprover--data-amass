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
# Save as a goejson file
#===================================================
def json_to_geojson(json_response, file_name):
    my_data = json_response['elements']            # -- response is json format 

    features_to_points = []
    for each_feature in my_data: 
        if 'tags' not in each_feature:
            each_feature['tags'] = 'Feature'
        else:
            pass

        if each_feature['type'] == 'node':                                # 'node' element
            features_to_points = features_to_points + [each_feature]

        elif each_feature['type'] == 'way' :                              # 'way' element
            try:
                LAT = [coordinate['lat'] for coordinate in each_feature['geometry']]
                LON = [coordinate['lon'] for coordinate in each_feature['geometry']]
                TYPE = ['node'] * len(LAT)
                ID = [each_feature['id']] * len(LAT)
                TAGS = [each_feature['tags']] * len(LAT)

                points = list(zip(TYPE, ID, LAT, LON, TAGS))   #-- parsing to points
                parsed_to_points = [{'type':point[0], 'id':point[1], 'lat':point[2], 'lon':point[3], 
                                     'tags':point[4]} for point in points]
                features_to_points = features_to_points + parsed_to_points 
            except:
                pass

        else:                                                             # 'relation' element
            parsed_relation = []
            index =  each_feature['id']
            tag = each_feature['tags']
            for member in each_feature['members']:
                try:
                    LAT = [coordinate['lat'] for coordinate in member['geometry']]
                    LON = [coordinate['lon'] for coordinate in member['geometry']]
                    TYPE = ['node'] * len(LAT)             
                    ID = [index] * len(LAT)
                    TAGS = [tag] * len(LAT)

                    points = list(zip(TYPE, ID, LAT, LON, TAGS))
                    parsed_to_way_to_point = [{'type':point[0], 'id':point[1], 'lat':point[2], 'lon':point[3], 
                                             'tags':point[4]} for point in points]
                except:
                    parsed_to_way_to_point = []
            parsed_relation = parsed_relation + parsed_to_way_to_point
            features_to_points = features_to_points + parsed_relation 

    json_response['elements'] = features_to_points
    feature_collection = overpass.as_geojson(json_response, 'point') 
    
    f_name = file_name + '.geojson'
    with open(f_name, 'w') as f:
        gj = json.dump(feature_collection, f)
        return gj
    
    return None

