# MapRover pipeline 1

This pipeline provides utilities to get sets of OpenStreetMap tiles which cover (or don't) instances of certain features of interest.

There are really two distinct steps in the 'pipeline'; the first fetches data about map features and turns it into a geometric representation. The input is a query with the following parameters:

- location, specified as a place name or as geographical coordinates (a Node or Polygon); if a Way is passed as a location it is closed into a polygon. Either form of input must be compatible with the OpenStreetMap Overpass API.
- map feature tag(s) and value(s), input as a dict. For example, to search for stables and stys (both are buildings) and for raceways (a kind of highway), the input dict would be

```python
{'building': ['stable','sty'], 'highway': 'raceway'}
```
- `search_radius`: if the location is a place name, we need to know how much of the surrounding area is considered in the search

- `search_shape`: if the location is a place name, should the 'radius' be interpreted as a circle or square?

- `include_partial`: should entities which partially overlap with the search region be counted and included in the result set?

This first step is in the works as `run_ql_query` in `TileGenerator.py`, which returns the JSON object from Overpass for further processing.

The second part concerns fetching map tiles which overlap the item(s) of interest. The reason to decouple this transaction from the first part is that we may wish to fetch tiles for the same object but at different zoom levels, or with different input parameters. However we need not redo the work in the first step for such refinements. Likewise, we might combine the result sets of a few different queries before fetching the matching tiles.

Parameters for this step:

- `z`: level of zoom (between 1 and 19 inclusive) at which tiles are extracted

- `n_pos`: desired number of tiles which are examples of the query. This is an upper bound since its possible that, given the zoom level, there are fewer than `n_pos` tiles in the area which satisfy the criterion.

- `n_neg`: desired number of tiles that are _not_ examples of the query. In theory this is also an upper bound for the same reason as `n_pos`.

- `qual`: the minimum 'quality' of the match needed for a given positive example to be returned. A `float` between 0 and 1 - this indicates the proportion of the tile that must be filled with the query polygon. The intended use is to pick some epsilon bounded away from zero which reduces 'false positive' tiles.

- `buffer`: if a Node or Way is part of the result set, then to make things consistent we need to add some buffer to them. This ensures each object compared is a polygon, so that everything gets treated consistently. The `buffer` quantity is how much buffer _as a proportion of grid tile size_ should be added to a 1-D object to flesh it out into a 2-d polygon. Obviously this interplays with the `qual` parameter. Usually we'd expect that a pretty small amount (0.02 - 0.1) is sufficient.

Here is a concerete example:

```python
w1 = shapely.geometry.LineString([(1,1),(2,2),(3,5),(6,7)])
w1.buffer(0.2)
```

The bounding box for this shape is 5x6 (check `w1.envelope.area == 30`) and adding a buffer of 0.2 (about 0.1 in proportion to the object width) creates a nicely-sized shape whose area is also about 10% (since the object is mostly linear)

