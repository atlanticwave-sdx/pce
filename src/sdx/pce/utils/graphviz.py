import re
import json

import networkx as nx
from networkx.algorithms import approximation as approx

from sdx.pce.utils.constants import Constants


def dot_file(topology_file, te_file=None):
    graph = nx.Graph(nx.nx_pydot.read_dot(topology_file))
    # graph = nx.Graph(nx.nx_agraph.read_dot(topology_file))
    num_nodes = graph.number_of_nodes()
    mapping = dict(zip(graph, range(num_nodes)))
    graph = nx.relabel_nodes(graph, mapping)

    for (u, v, w) in graph.edges(data=True):
        if "capacity" not in w.keys():
            bandwidth = 1000.0
        else:
            capacity = w["capacity"].strip('"')
            bw = re.split(r"(\D+)", capacity)
            bandwidth = bw[0]
            if bw[1].startswith("G"):
                bandwidth = float(bw[0]) * 1000

        w[Constants.ORIGINAL_BANDWIDTH] = float(bandwidth)
        w[Constants.BANDWIDTH] = float(bandwidth)
        w[Constants.WEIGHT] = float(w["cost"])
        if "latency" not in w.keys():
            latency = 10
            w[Constants.LATENCY] = latency

    connectivity = approx.node_connectivity(graph)
    print("Connectivity:" + str(connectivity))

    with open(te_file) as f:
        tm = json.load(f)
    o_tm = []
    for t in tm:
        tr = tuple(t)
        o_tm.append(tr)

    return graph, o_tm
    # connection = GetConnection('../test/data/test_connection.json')
    # g = GetNetworkToplogy(25,0.4)
    # print(lbnxgraphgenerator(25, 0.4,connection,g))
