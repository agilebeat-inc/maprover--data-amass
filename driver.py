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

pos_file, neg_file = 'ES_mil_pos.tsv', 'ES_mil_neg.tsv'
pdir, ndir = pos_file.split('.')[0], neg_file.split('.')[0]
max_tiles = 10 # just testing

# create the xyz tile 'database':
# import os
# os.chdir('/mnt/c/Users/skm/Dropbox/AgileBeat')
pipe1.sh_creator(ES_mil,[17,18,19],pos_file,neg_file)

# running the shell commands:
import subprocess as sp

# note that we need to change the working directory or 
# supply the path to the download_tiles script
sp.run(f"bash download_tiles.sh -f {pos_file} -o {pdir} -n {max_tiles}",shell = True)
sp.run(f"bash download_tiles.sh -f {neg_file} -o {ndir} -n {max_tiles}",shell = True)

# optional: filter out empty tiles in negative data set
empty_imgs = pipe1.filter_size(ndir,650)
pipe1.apply_filter(ndir,[e[0] for e in empty_imgs],'junk')

# second approach: use Shapely to sample tiles that overlap
# with the geometric object, specifying min/max overlap if desired
# qq = process_query(ES_mil,17)
# spots = calc_map_locations(qq)

# positive_dataset(qq,pdir)
# negative_dataset(qq,ndir)
