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
    tag = 'military',
    values = ['airfield','bunker']
    buffersize = 200000,
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

if False:
    # more examples/testing
    import os
    if os.getcwd().startswith('/tmp/'):
        os.chdir("/mnt/c/Users/skm/Dropbox/AgileBeat/pipeline-1")
    
    # more example queries
    q1 = run_ql_query(90210,'leisure',values = ['park'],5000)
    qq_nodes = atomize_features(qq)

    CN_mil = run_ql_query(
        place = "Beijing, China", buffersize = 200000, 
        tag = 'military', values = ['airfield']
    )

    # from query_helpers import run_ql_query
    # test that ways and relations are correctly processed:
    # this query should return 8 ways and 2 relations
    # qq = run_ql_query('San Juan, Puero Rico','landuse',['forest'],10000)
    qq = run_ql_query(
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
    qp = process_query(qq,17,min_ovp = 0.2,max_ovp = 0.9)
    pos_df = positive_dataset(qp,'/mnt/c/Users/skm/Dropbox/Agilebeat/tstp')
    pos_df.to_csv(
        path_or_buf = pdir + '/tile_info.tsv',
        sep = '\t',
        header = True,
        index = False
    )
    neg_df = negative_dataset(qp,'/mnt/c/Users/skm/Dropbox/Agilebeat/tstn')

    # each element in the 'tiles' list is a tuple of (tile,intersection)
    pw = process_way(qq['elements'][2],max_ovp = 0.8)
    unary_union([p[0] for p in pw])
