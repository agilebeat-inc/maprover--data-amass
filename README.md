# MapRover pipeline 1

This pipeline provides utilities to get sets of OpenStreetMap tiles which overlap (or don't) instances of certain features of interest.

There are three steps in the 'pipeline', each of which has a separate submodule:
1. creating a query that gets items of interest in a specific geographical region. `run_ql_query` in `query_helpers.py` handles this part, and its return value is used in the other steps
2. Given the query results of step 1, find OSM tiles corresponding to the query elements. There are two approaches, `sh_creator` in `downloading.py` is simpler but faster; the second approach is documented in `query_processing.py` and uses Shapely. The latter should be more configurable but the tile conversion is still in progress and currently imperfect. 
3. Having identified a set of tiles, download them. There are currently two implementations corresponding to the differences in step 2; perhaps this should get redone. In the first case, running `sh_creator` will create two tab-delimited output files for the positive and negative datasets respectively. These just contain the tile coordinates data and should be input as the `--file` or `-f` argument to `download_tiles.sh`. That script does the actual downloading along with some basic error checking.

Concretely, for a given pair of output files, run

```bash
bash download_tiles.sh -f pos_file.tsv -o ./pos_imgs
bash download_tiles.sh -f neg_file.tsv -o ./neg_imgs -n 500
```

The `-n 500` in the latter command restricts the download to the first 500 tiles in `neg_file.tsv`. It is very important to run this command with distinct `-o` values since otherwise the images will get mixed together!

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
# now call sh_creator to output the 'positive' and 'negative' training sets
zoom_levels = [18,19]
pipe1.sh_creator(Thessaloniki_beaches,zoom_levels,'is_beach.tsv','not_beach.tsv')
```

Now, to download the tiles we can run the bash script `download_tiles.sh` with each input (making sure to save the images in different output directories):

```bash
./download_tiles.sh --file is_beach.tsv --outdir ./thessa_beach
./download_tiles.sh -f not_beach.tsv -o ./thessa_not_beach -n 200
```

Short versions of the commands in the second case are used for illustration, and the `-n 200` means only the first 200 tiles in `not_beach.tsv` will be downloaded. Any files that did not download successfully will have their URLs written to `failed.txt` within the output folder.

So now there should be two folders, `thessa_beach` and `thessa_not_beach` which have tiles.

_Optional_ if we'd like to filter out tiles that are effectively empty, we can run `post_filtering.py` to either delete them or move them into a different directory. Here's an example:

```bash
python3 post_filtering.py --dir=./thessa_not_beach --min_size=600 -o=junk
```

This moves all tiles whose file size is less than 600 bytes into a subdirectory `junk` so that they can be easily ignored when the training tiles get read in to other programs.

We could have also done all of this from within a single Python script; again, see the `driver.py` code.