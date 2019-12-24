#! /usr/bin/env python3

"""
example of pipeline 1
1) creating a query via Overpass API
2) processing query to get map tiles
3) downloading map tiles and saving their metadata
"""

import os
if os.getwd().startswith('/tmp/'):
    os.setwd("/mnt/c/Users/skm/Dropbox/AgileBeat/pipeline-1")

from query_helpers import run_ql_query
from query_processing import process_query
from downloading import sh_creator, positive_dataset, negative_dataset

# first approach: take any tile in which any query node appears
# as a positive example, and any other tile in the bounding box
# as a negative example:
# should run the script 'download_tiles.sh' and input
# the output file (for positive and negative respectively)
ES_mil = run_ql_query(place = "Madrid, Spain", 
    buffersize = 200000, 
    tag = 'military', values = ['airfield','bunker'])

os.chdir("/mnt/c/Users/skm/Dropbox/AgileBeat/pipeline-1")
sh_creator(ES_mil,[17,18,19],'ES_testpos.tsv','ES_testneg.tsv')

# second approach: use Shapely to sample tiles that overlap
# with the geometric object, specifying min/max overlap if desired
qq = process_query(ES_mil,17)
# spots = calc_map_locations(qq)

positive_dataset(qq,'/mnt/c/Users/skm/Documents/test_picz')
negative_dataset(qq,'/mnt/c/Users/skm/Documents/test_picz')
