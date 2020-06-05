# MapRover pipeline 1

This pipeline provides utilities to get sets of OpenStreetMap tiles which overlap (or don't) instances of certain features of interest.

There are three steps in the 'pipeline', each of which has a separate submodule:
1. creating a query that gets items of interest in a specific geographical region. `run_ql_query` in `query_helpers.py` handles this part, and its return value is used in the other steps
2. Given the query results of step 1, find OSM tiles corresponding to the query elements. There are two approaches in `query_processing.py`; `create_tileset` is simpler but faster since it simply explodes all the results into individual nodes, then finds any tiles that overlap with any nodes. The second approach is implemented in  `process_query` and uses Shapely. There are `min_ovp` and `max_ovp` parameters which filter matching tiles to ones that overlap with an area of interest (when it is a Polygon and not a point) by a min. or max. amount.
3. Having identified a set of tiles, download them. For now, use the `save_tiles` function, which will download all the tiles from the input dataframe (created by `create_tileset`).

The file `driver.py` has example code showing how the parts work together.

## Installation

Run the script `pkginstall.sh` to install the pipeline-1 code as a Python module (this helps avoid tricky file-path issues).

## Dataset organization

After downloading some images, it may be useful to do a little quality control. Especially for negative datasets, there may be (practically) empty images which are not informative for training. The script `post_filtering.py` can automate cleanup of such files; consult its help documentation for details. Basically, we can filter by image size or entropy.

Once we have positive and negative sets of images for a particular query, they should be stored in a consistent way. __TBD__: what is the organizaitional setup for the various sets of trainig tiles.

## Full Example 

Here is an example showing all the steps:

Following what's in `driver.py`, say we want to find the beaches within 25000 meters of Thessaloniki:

```python
### (1) Import libraries¶
import warnings
warnings.filterwarnings('ignore')
import pipe1
import numpy as np


### (2) The function returns JSON result of an Overpass API query, with some extra metadata about the query appended.
leisure_park = pipe1.run_ql_query(
                place = "Auckland, New Zealand", buffersize=30000, 
                tag='leisure', values=['park']) 

# check some basic info about the returned query:
print(leisure_park['query_info'])


### (3) The function returns dictionary with two pandas.DataFrame: 'positive' and 'negative'
zoom_levels = [17, 18]
dfs = pipe1.basic_tileset(leisure_park, zoom_levels, 
      buffer = 3, n_neg = 1000)


### (4) Create the 'positive' and 'negative' training sets
posdir = './data/park'
negdir = './data/not_park'

num_pos_tiles = 500  # must be same as or smaller than #rows of dfs
n_pos = list(np.random.choice(dfs['positive'].shape[0], num_pos_tiles))

num_neg_tiles = 500  # must be same as or smaller than #rows of dfs
n_neg = list(np.random.choice(dfs['negative'].shape[0], num_neg_tiles))


### (5) Save tiles
pipe1.save_tiles(dfs['positive'].iloc[n_pos, :], posdir)
pipe1.save_tiles(dfs['negative'].iloc[n_neg, : ],negdir)
```

It's probably a good idea to also save the dataframes in the same directory where the tiles were downloaded:

```python
dfs['positive'].to_csv(
    path_or_buf = posdir + '/tile_info.tsv',
    sep = '\t',
    header = True,
    index = False
)
dfs['negative'].to_csv(
    path_or_buf = negdir + '/tile_info.tsv',
    sep = '\t',
    header = True,
    index = False
)
```

So now there should be two folders, `park` and `not_park` which have tiles and the associated metadata.

_Optional_ if we'd like to filter out tiles that are effectively empty, we can run `post_filtering.py` to either delete them or move them into a different directory. Here's an example:

```python
empty_imgs = pipe1.filter_size(negdir, 650)  # returns list of tuples (file, size)

junk = './data/junk'
pipe1.apply_filter(negdir,[e[0] for e in empty_imgs], junk)
```

This moves all tiles whose file size is less than 600 bytes into a subdirectory `junk` so that they can be easily ignored when the training tiles get read in to other programs.


## Future Improvement
* false positive tiles: the limitation of using overpass API is that false positive tiles are possibly collected since it response to a query based on _tag_:_value_ information. As a result, it returns any tiles with requested _tag_ and _values_ even though tiles do not contains the requested object.  
The issue seems to be improved by using ```shapely``` library. 
 