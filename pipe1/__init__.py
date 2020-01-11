# functions exported at top level for convenience
from .query_helpers import run_ql_query
from .downloading import create_tileset, save_tiles
from .post_filtering import filter_size, filter_entropy, apply_filter
from .query_processing import process_query # in development!

__all__ = [
    'run_ql_query','create_tileset','save_tiles','filter_size',
    'filter_entropy','apply_filter','process_query'
]

__version__ = "0.0.2" # does not get exported into package namespace by setup.py