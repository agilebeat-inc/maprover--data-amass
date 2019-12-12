import json
import math
import numpy as np

def load_json_file(path):
    with open(path, 'r') as in_file:
        gj = json.load(in_file)
        return gj

def convert_points_along_polyline_to_line_segments(line_segment):
    line_segment.insert(0, [None, None])
    line_segment.append([None, None])
    return zip(line_segment[::2], line_segment[1::2])

def generate_points_along_line_segment(line_segment,n_points = 50):
    x0, y0 = line_segment[0]
    x1, y1 = line_segment[1]
    xC = np.linspace(x0,x1,num = n_points)
    yC = np.linspace(y0,y1,num = n_points)
    return [(x,y) for x,y in zip(xC,yC)]

def deg2num(lat_deg, lon_deg, zoom):
  lat_rad = math.radians(lat_deg)
  n = 2.0 ** zoom
  xtile = (n / 360) * (lon_deg + 180)
  ytile = (n / 2) * (1.0 - math.asinh(math.tan(lat_rad))/math.pi)
  return (int(xtile), int(ytile))


def num2deg(xtile, ytile, zoom):
  n = 2.0 ** zoom
  lon_deg = 360 * xtile / n - 180
  lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
  lat_deg = math.degrees(lat_rad)
  return (lat_deg, lon_deg)


def generate_geojson(points):
    geojson = {'type': 'FeatureCollection', 'features': []}
    for p in points:
        feature = {'type': 'Feature',
                   'properties': {},
                   'geometry': {'type': 'Point',
                                'coordinates': [p[0],p[1]]}}
        geojson['features'].append(feature)
    return geojson