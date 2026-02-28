"""Dependency mapping: wire output of one pipeline node into the input of another.

Usage: standalone snippet showing Dependency configuration.
"""
from datapizza.pipeline import Dependency

dep = Dependency(
    node_name="load_data", # node to get data from
    input_key="result", # Optional: specific key from output
    target_key="data", # Key in receiving node's input
)
