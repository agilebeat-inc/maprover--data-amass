# MapRover pipeline 1

This pipeline provides utilities to get sets of OpenStreetMap tiles which overlap (or don't) instances of certain features of interest.

There are three steps in the 'pipeline', each of which has a separate submodule:
1. creating a query that gets items of interest in a specific geographical region. `run_ql_query` in `query_helpers.py` handles this part, and its return value is used in the other steps
2. Given the query results of step 1, find OSM tiles corresponding to the query elements. There are two approaches, `create_tileset` in `downloading.py` is simpler but faster; the second approach is documented in `query_processing.py` and uses Shapely. The latter should be more configurable but the tile conversion is still in progress and currently imperfect. 
3. Having identified a set of tiles, download them. For now, use the `save_tiles` function, which will download all the tiles from the input dataframe (created by `create_tileset`).

The file `driver.py` has example code showing how the parts work together.

## Installation

Run the script `pkginstall.sh` to install the pipeline-1 code as a Python module (this helps avoid tricky file-path issues).

## Dataset organization

After downloading some images, it may be useful to do a little quality control. Especially for negative datasets, there may be (practically) empty images which are not informative for training. The script `post_filtering.py` can automate cleanup of such files; consult its help documentation for details. Basically, we can filter by image size or entropy.

Once we have positive and negative sets of images for a particular query, they should be stored in a consistent way. __TBD__: what is the organizaitional setup for the various sets of trainig tiles.

## full example

Here is an example showing all the steps:

First, run a Python script similar to what's in `driver.py`. Say we want to find the beaches within 25000 meters of Thessaloniki:

```python
import pipe1

Thessaloniki_beaches = pipe1.run_ql_query(
    place = "Thessaloniki",buffersize = 25000,
    tag = 'natural',values = ['beach']
)
# check some basic info about the returned query:
print(Thessaloniki_beaches['query_info'])
# next, create the 'positive' and 'negative' training sets
zoom_levels = [18,19]
dfs = pipe1.create_tileset(Thessaloniki_beaches,zoom_levels,buffer = 5)
posdir = './thessa_beach'
negdir = './thessa_not_beach'
num_tiles = 50 # let's save this many tiles
pipe1.save_tiles(dfs['positive'].head(num_tiles),posdir)
pipe1.save_tiles(dfs['negative'].head(num_tiles),negdir)
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

So now there should be two folders, `thessa_beach` and `thessa_not_beach` which have tiles and the associated metadata.

_Optional_ if we'd like to filter out tiles that are effectively empty, we can run `post_filtering.py` to either delete them or move them into a different directory. Here's an example:

```python
empty_imgs = pipe1.filter_size(negdir,650)
pipe1.apply_filter(negdir,[e[0] for e in empty_imgs],'junk')
```

This moves all tiles whose file size is less than 600 bytes into a subdirectory `junk` so that they can be easily ignored when the training tiles get read in to other programs.
