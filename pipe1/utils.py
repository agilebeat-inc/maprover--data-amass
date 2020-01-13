import math
import numpy as np

# def polyline_to_segments(polyline):
#     polyline.insert(0, [None, None])
#     polyline.append([None, None])
#     return zip(polyline[::2], polyline[1::2])

# def points_along_line_segment(line_segment,n_points = 50):
#     x0, y0 = line_segment[0]
#     x1, y1 = line_segment[1]
#     xC = np.linspace(x0,x1,num = n_points)
#     yC = np.linspace(y0,y1,num = n_points)
#     return [(x,y) for x,y in zip(xC,yC)]

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

  def sample_complement(xx,yy,n,buffer = 0):
    """ 
    Take a sample from the bounding box of the elements in xx and yy.
    The pairs [(x,y) for x,y in zip(xx,yy)] are not included in the sample;
    we are sampling from the complement of such elements.
    Args:
        xx: iterable of ints or other discrete elements
        yy: iterable of ints or other discrete elements
        n: number of items sampled from the complement of Cartesian product of xx and yy
        buffer: int; if positive, each element in the sample must be at least this far away
        from a 'positive' element
    Returns:
        tuple newx,newy which are lists of items of the same type as xx and yy
    Raises:
        ValueError for a few edge cases
    """

    n_pos = len(xx)
    if len(yy) != n_pos:
        msg = f"sample_complement: lengths of {xx} and {yy} must match!"
        raise ValueError(msg)
    x_min, x_max, y_min, y_max = min(xx), max(xx), min(yy), max(yy)
    xrng, yrng = range(x_min, x_max+1), range(y_min,y_max+1)

    # get an equal number of 'negative' points which are in the bounding box
    n_in_box = len(xrng) * len(yrng)
    print(f"{n_pos} positive tiles; {n_in_box} tiles in area")
    # edge case - we sampled a solid rectangle of tiles
    if n_pos >= n_in_box:
        msg = f"sh_creator: {n_pos} positive tiles and {n_in_box} total tiles!"
        raise ValueError(msg)

    n_neg = min(n_in_box - n_pos,n)
    pos_xy, neg_xy = set((x,y) for x,y in zip(xx,yy)), set()
    XY = np.array(list(pos_xy))
    rng = np.random.default_rng()

    def min_dist(x,y):
        dd = np.sum(np.square(XY - (x,y)),axis = 1)
        return np.sqrt(min(dd))

    # if the buffer is large, there may not be enough tiles
    # but its not possible to calculate beforehand
    tries = 0 # another good walrus candidate
    while len(neg_xy) < n_neg:
        tries += 1
        if tries > 5: break
        newx = rng.integers(x_min,x_max,n_neg,endpoint=True)
        newy = rng.integers(y_min,y_max,n_neg,endpoint=True)
        nearest_d = [min_dist(x,y) for x,y in zip(newx,newy)]
        if buffer >= 1:
            neg_xy.update((x,y) for x,y,d in zip(newx,newy,nearest_d) if d > buffer)
        else:
            neg_xy.update((x,y) for x,y in zip(newx,newy) if (x,y) not in pos_xy)

    neg_xy = list(neg_xy)[:n_neg]
    return [e[0] for e in neg_xy], [e[1] for e in neg_xy]

# defining the size of tiles (in terms of latitude/longitude)
# for a given zoom level and (lat,lon)
# longitude is easy; # tiles is simply 2^z so tile width is 2^-z
# latitude depends on the location
# however a tile should be 'square' so must these match up?
# it doesn't necessarily matter so long as the relationship is monotone
# and provides enough range (i.e. at most zoom levels, tiles are not)
# 'too big' or 'too small'
def tile_size(y,zoom):
    width = 2 ** -zoom
    height = num2deg(0,y,zoom)[1]
    return width, height

