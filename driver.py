#! /usr/bin/env python3

"""
example of pipeline 1
1) creating a query via Overpass API
2) processing query to get map tiles
3) downloading map tiles and saving their metadata
"""

import pipe1

# first approach: take any tile in which any query node appears
# as a positive example, and any other tile in the bounding box
# as a negative example:

ES_mil = pipe1.run_ql_query(
    place = "Madrid, Spain", 
    buffersize = 200000, 
    tag = 'military', values = ['airfield','bunker']
)


# create positive and negative tile sets:
dfs = pipe1.create_tileset(ES_mil,[17,18,19],buffer = 5)
# PUT YOUR OWN DIRECTORY HERE:
basedir = '/mnt/c/Users/skm/Dropbox/AgileBeat'
pdir, ndir = basedir + '/testpos', basedir + '/testneg'
max_tiles = 10 # just testing

# now we can download the tiles:
pipe1.save_tiles(dfs['positive'].head(max_tiles),pdir)
pipe1.save_tiles(dfs['negative'].head(max_tiles),ndir)
# may also want to save the data sets:
# can always still use download_tiles shell script to
# get tiles from this file at a later time
dfs['positive'].to_csv(
    path_or_buf = pdir + '/tile_info.tsv',
    sep = '\t',
    header = True,
    index = False
)
dfs['negative'].to_csv(
    path_or_buf = ndir + '/tile_info.tsv',
    sep = '\t',
    header = True,
    index = False
)
# optional: filter out empty tiles in negative data set
empty_imgs = pipe1.filter_size(ndir,650)
pipe1.apply_filter(ndir,[e[0] for e in empty_imgs],'junk')

# second approach: use Shapely to sample tiles that overlap
# with the geometric object, specifying min/max overlap if desired
# qq = process_query(ES_mil,17)
# spots = calc_map_locations(qq)

# positive_dataset(qq,pdir)
# negative_dataset(qq,ndir)
