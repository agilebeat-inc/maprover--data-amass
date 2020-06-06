### (1) Import libraries¶
import warnings
warnings.filterwarnings('ignore')
import pipe1


### (2) The function returns JSON result of an Overpass API query, with some extra metadata about the query appended.¶
leisure_park = pipe1.run_ql_query(
    place = "Auckland, New Zealand", 
    buffersize=30000, tag='leisure', values=['park']
)


### (3) The function returns dictionary with two pandas.DataFrame: 'positive' and 'negative'
zoom_levels = [17, 18]
dfs = pipe1.basic_tileset(leisure_park, zoom_levels, buffer = 3, n_neg = 1000)


### (4) Specify directories
# directories where positive (posdir) and negative (negdir) tiles will be saved, the number of tiles (num_pos_tiles, num_neg_tiles)
posdir = '~/maprover--data-amass/data_leisure_park/park'
negdir = '~/maprover--data-amass/data_leisure_park/not_park'

num_pos_tiles = 50  # must be same as or smaller than #rows of dfs
pos_download = dfs['positive'].sample(n=num_pos_tiles)

num_neg_tiles = 50  # must be same as or smaller than #rows of dfs
neg_download = dfs['negative'].sample(n=num_neg_tiles)

### (5) Save tiles
pipe1.save_tiles(pos_download, posdir)
pipe1.save_tiles(neg_download, negdir)