#! /usr/bin/env python3

"""
example of pipeline 1
1) creating a query via Overpass API
2) processing query to get map tiles
3) downloading map tiles and saving their metadata
"""

import pipe1
from pipe1 import save_tsv

# first approach: take any tile in which any query node appears
# as a positive example, and any other tile in the bounding box
# as a negative example:

ES_mil = pipe1.run_ql_query(
    place = "Madrid, Spain", 
    tag = 'military',
    values = ['airfield','bunker'],
    buffersize = 200000
)

# create positive and negative tile sets:
# approx. how many elements will be in positive dataset?
atoms = pipe1.query_helpers.atomize_features(ES_mil)
# get 50% more negative tiles than positive
# note that its harder to exactly specify the # of positive tiles
# up front; the # of negative is usually easier to satisfy
num_neg = int(1.5 * len(atoms))
print(f"Looking for up to {len(atoms)} positive and {num_neg} negative tiles!")
dfs = pipe1.basic_tileset(ES_mil,[17,18,19],buffer = 100,n_neg = num_neg)

# check out the sampling and buffer:

# also check out the sizes before downloading!
np, nn = dfs['positive'].shape[0], dfs['negative'].shape[0]
print(f"We actually determined locations for {np} and {nn} +/- tiles.")
pipe1.plot_tiles(dfs,tile_size = 6)

# PUT YOUR OWN DIRECTORY HERE:
basedir = '/mnt/c/Users/skm/Dropbox/AgileBeat'
pdir, ndir = basedir + '/testpos', basedir + '/testneg'
max_tiles = 20 # just testing

# now we can download the tiles:
pipe1.save_tiles(dfs['positive'].head(max_tiles),pdir + '/basic')
pipe1.save_tiles(dfs['negative'].head(max_tiles),ndir + '/basic')
# may also want to save the data sets:
# can always still use download_tiles shell script to
# get tiles from this file at a later time
save_tsv(dfs['positive'],pdir + '/tile_info_basic.tsv')
save_tsv(dfs['negative'],ndir + '/tile_info_basic.tsv')


# approach with Shapely
# we shouldn't really need to distinguish between 'negative' tiles
# but for illustration purposes, both sets are saved into distinct
# directories compared to the 'basic' approach
qp = pipe1.process_query(ES_mil,17,min_ovp = 0.2,max_ovp = 0.9)
shdf = shapely_tileset(qp,min_ovp = 0.2,max_ovp = 0.98,n_neg = 500,buffer = 15)
dfp2 = save_tiles(shdf['positive'],pdir + '/shapely')
dfn2 = save_tiles(shdf['negative'],ndir + '/shapely')
save_tsv(dfp2,pdir + '/tile_info_shapely.tsv')
save_tsv(dfn2,ndir + '/tile_info_shapely.tsv')

# optional: filter out empty tiles in negative data set
empty_imgs = pipe1.filter_size(ndir + '/basic',650)
pipe1.apply_filter(ndir,[e[0] for e in empty_imgs],'junk')

if False:
    # more examples/testing
    import os
    if os.getcwd().startswith('/tmp/'):
        os.chdir("/mnt/c/Users/skm/Dropbox/AgileBeat/pipeline-1")
    
    q1 = pipe1.run_ql_query(90210,'leisure',values = ['park'],5000)
    qq_nodes = pipe1.atomize_features(qq)

    CN_mil = pipe1.run_ql_query(
        place = "Beijing, China", buffersize = 200000, 
        tag = 'military', values = ['airfield']
    )

    # from query_helpers import run_ql_query
    # test that ways and relations are correctly processed:
    # this query should return 8 ways and 2 relations
    # qq = run_ql_query('San Juan, Puero Rico','landuse',['forest'],10000)
    qq = pipe1.run_ql_query(
        place = "Madrid, Spain", 
        buffersize = 200000, 
        tag = 'military', values = ['airfield']
    )
    rels = [e for e in qq['elements'] if e['type'] == 'relation']
    wayz = [e for e in qq['elements'] if e['type'] == 'way']
    # will the ways be processed as lines or polygons?
    for w in wayz:
        # the horrendously inefficient JSON encoding:
        coordz = [(e['lat'],e['lon']) for e in w['geometry']]
        clzd = is_basically_closed(coordz)
        if clzd:
            print("This way is closed!")
        else:
            print("This way is open!")
    # may want to impose validity conditions: filter self-intersecting ways
    # coordinating with save_tiles function: need to get all the x/y coordinates
    qp = pipe1.process_query(qq,17,min_ovp = 0.2,max_ovp = 0.9)
    outdir = '/mnt/c/Users/skm/Dropbox/Agilebeat'

    pos_df = pipe1.positive_dataset(qp,outdir + '/tstp')
    save_tsv(pos_df,outdir + '/tstp/tile_info.tsv')
    
    neg_df = pipe1.negative_dataset(qp,outdir + '/tstn')
    save_tsv(pos_df,outdir + '/tstn/tile_info.tsv')

    # each element in the 'tiles' list is a tuple of (tile,intersection)
    # pw = process_way(qq['elements'][2],max_ovp = 0.8)
    # unary_union([p[0] for p in pw])
