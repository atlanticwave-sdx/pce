"""
Handlers for topology description in Graphviz dot format.

Topology description in dot format used to be popular.  There exist
dot files for several well-known networks like Geant, and they were
used for the algorithm performance study, and of course it extended
SDX to support one more topology description format potentially from
OXPs.

This is optional since this needs's networkx's support for dot file
format is changing -- networkx's dot file support used pydot, but
pydot is being deprecated in favor of pygraphviz:

https://github.com/networkx/networkx/issues/5723

Pydot is "pure" Python, and pygraphviz is implemented as bindings to
graphviz C library, so installing the latter is a little more work.
"""

import json
import re
from pathlib import Path

import networkx as nx
from networkx.algorithms import approximation as approx

from sdx.pce.utils.constants import Constants

__all__ = ["can_read_dot_file", "read_dot_file"]


def can_read_dot_file() -> bool:
    """
    See if we have pygraphviz or pydot installed.
    """
    try:
        # try to read dot file using pygraphviz
        nx.nx_agraph.read_dot(None)
        return True
    except ImportError as e:
        print(f"pygraphviz doesn't seem to be available: {e}")
        return False


def read_dot_file(topology_file: str | Path) -> nx.Graph:
    """
    Read a Graphviz dot file and return a graph.
    """
    # try to read dot file using pygraphviz
    graph = nx.Graph(nx.nx_agraph.read_dot(topology_file))

    # If we must use pydot, use the line below:
    # graph = nx.Graph(nx.nx_pydot.read_dot(topology_file))

    num_nodes = graph.number_of_nodes()
    mapping = dict(zip(graph, range(num_nodes)))
    graph = nx.relabel_nodes(graph, mapping)

    for (u, v, w) in graph.edges(data=True):
        if "capacity" not in w.keys():
            bandwidth = 1000.0
        else:
            capacity = w["capacity"].strip('"')
            bw = re.split(r"(\D+)", capacity)
            bandwidth = float(bw[0])
            if bw[1].startswith("G"):
                bandwidth = float(bw[0]) * 1000

        w[Constants.ORIGINAL_BANDWIDTH] = float(bandwidth)
        w[Constants.BANDWIDTH] = float(bandwidth)
        w[Constants.WEIGHT] = float(w["cost"])
        if Constants.LATENCY not in w.keys():
            latency = 10
            w[Constants.LATENCY] = latency

    connectivity = approx.node_connectivity(graph)
    print(f"Connectivity: {connectivity}")

    return graph
