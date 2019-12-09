import json
import math
import random
import string

def load_json_file(path):
    with open(path, 'r') as in_file:
        gj = json.load(in_file)
        return gj
    return None


def extract_feature_list_from_gj(gj):
    fl = [f for f in gj['features']]
    return fl


def extract_line_coordinates_from_feature(feature):
    line_coords = feature['geometry']['coordinates']
    return line_coords


def convert_points_along_polyline_to_line_segments(line_segment):
    line_segment.insert(0, [None, None])
    line_segment.append([None, None])
    return zip(line_segment[::2], line_segment[1::2])

def generate_points_along_line_segment(line_segment):
    x0, y0 = line_segment[0]
    x1, y1 = line_segment[1]
    points = []
    if x0 is None:
        points = [[x1, y1]]
    elif x1 is None:
        points = [[x0, y0]]
    elif abs(x0 - x1) < 0.001:
        points = [[x0, y0]]
    else:
        dx = x1 - x0;
        dy = y1 - y0;
        offset = 0
        while x0 < x0 + offset < x1:
            curr_x = x0 + offset
            curr_y = curr_x * dy/dx
            points.append([x0+offset, curr_y])
            offset = offset + 0.001
        points.append([x1, y1])
    return points

def generate_points_within_polygon(polygon):
    pass
    return points

def deg2num(lat_deg, lon_deg, zoom):
  lat_rad = math.radians(lat_deg)
  n = 2.0 ** zoom
  xtile = int((lon_deg + 180.0) / 360.0 * n)
  ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
  return (xtile, ytile)


import math
def num2deg(xtile, ytile, zoom):
  n = 2.0 ** zoom
  lon_deg = xtile / n * 360.0 - 180.0
  lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
  lat_deg = math.degrees(lat_rad)
  return (lat_deg, lon_deg)


def generate_geojson(points):
    geojson = {'type': 'FeatureCollection', 'features': []}
    for p in points:
        feature = {'type': 'Feature',
                   'properties': {},
                   'geometry': {'type': 'Point',
                                'coordinates': []}}
        feature['geometry']['coordinates'] = [p[0], p[1]]
        geojson['features'].append(feature)
    return geojson