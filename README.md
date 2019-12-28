# MapRover pipeline 1

This pipeline provides utilities to get sets of OpenStreetMap tiles which overlap (or don't) instances of certain features of interest.

There are three steps in the 'pipeline', each of which has a separate submodule:
1. creating a query that gets items of interest in a specific geographical region.  `run_ql_query` in `query_helpers.py` handles this part, and its return value is used in the other steps
2. Given the query results of step 1, find OSM tiles corresponding to the query elements. There are two approaches, `sh_creator` in `downloading.py` is simpler but faster; the second approach is documented in `query_processing.py` and uses Shapely. The latter should be more configurable but the tile conversion is still in progress and currently imperfect. 
3. Having identified a set of tiles, download them. There are currently two implementations corresponding to the differences in step 2; perhaps this should get redone.

The file `driver.py` has example code showing how the parts work together.

# Dataset organization

After downloading some images, it may be useful to do a little quality control. Especially for negative datasets, there may be (practically) empty images which are not informative for training. The script `post_filtering.py` can automate cleanup of such files; consult its help documentation for details. Basically, we can filter by image size or entropy.

Once we have positive and negative sets of images for a particular query, they should be stored in a consistent way. __TBD__: what is the organizaitional setup for the various sets of trainig tiles.