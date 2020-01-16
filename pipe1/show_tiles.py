import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
from matplotlib import cm # color maps


# need to choose two darkish but distinct colors for
# positive vs. negative tiles since they're kinda hard to
# see against white bg

# first prepare all the data
# 'class' values are indices into the color palette
# which can be defined
def plot_tiles(tiles,zoom = None,tile_size = 5):
    """
    Show positions of positive and negative tiles

    Args:
        tiles: the output of `create_tileset` function (dict with 'positive' and 'negative' dataframes)
        zoom: int, optional: level of zoom for which tiles are plotted if `tiles` has mutiple zooming levels
    """

    dp = tiles['positive']
    dp['class'] = 0
    dn = tiles['negative']
    dn['class'] = 1

    dc = pd.concat([dp,dn],axis = 0)
    if zoom is None: # choose first zoom if user didn't specify
        zoom = dc['z'].array[0]
    dz = dc[dc['z'] == zoom] 

    # x = np.array([1,4,5,8,10])
    # y = np.array([0,4,0,2,0])
    # cc = np.array([0,1,0,1,0])
    # dz = {'x': x,'y': y,'class': cc}
    adj = 0.5 * tile_size
    rects = [Rectangle((x - adj,y - adj),width = tile_size,height = tile_size,alpha = 0.5) \
        for x,y in zip(dz['x'],dz['y'])]

    # create collection of patches for IFU position
    Rekts = PatchCollection(rects,cmap = cm.Dark2)
    Rekts.set_array(dz['class'])

    # set aspect ratio according to bounding box:
    width, height = np.ptp(dz['x']), np.ptp(dz['y'])
    pw, ph = 9, 9
    if width > height:
        ph *= height / width
    else:
        pw *= width / height

    fig = plt.figure(figsize = (pw,ph))
    ax = plt.axes([0.1,0.1,0.7,0.7])
    plt.xlabel('x (Longitude)')
    plt.ylabel('y (Latitude)')
    # https://matplotlib.org/3.1.1/gallery/statistics/errorbars_and_boxes.html#sphx-glr-gallery-statistics-errorbars-and-boxes-py
    ax.add_collection(Rekts)
    plt.axis('scaled')
    plt.show()
