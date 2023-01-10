#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  8 13:34:06 2022

@author: Yufeng Xin (yxin@renci.org)
"""
import json
import random
import re

import networkx as nx
import pylab as plt
from networkx.algorithms import approximation as approx
from networkx.generators.random_graphs import erdos_renyi_graph

from sdx.pce.utils.constants import Constants
from sdx.pce.utils.functions import GraphFunction


class RandomTopologyGenerator:
    def __init__(
        self,
        num_node,
        link_probability=0.2,
        l_bw=Constants.MIN_L_BW,
        u_bw=Constants.MAX_L_BW,
        l_lat=Constants.MIN_L_LAT,
        u_lat=Constants.MAX_L_LAT,
        seed=2022,
    ):
        """
        :param num_nodes: Total number of the random network's nodes
        :param link_probability: Link creation probability.
        """
        random.seed(seed)
        self.seed = seed

        self.num_node = num_node
        self.link_probability = link_probability

        self.low_bw = l_bw
        self.upper_bw = u_bw
        self.low_latency = l_lat
        self.upper_latency = u_lat

        self.graphFunction = GraphFunction()

    def bw_range(self, l_bw, u_bw):
        self.low_bw = l_bw
        self.upper_bw = u_bw

    def latency_range(self, l_lat, u_lat):
        self.low_latency = l_lat
        self.upper_latency = u_lat

    def set_graph(self, g):
        self.graph = g

    def get_graph(self):
        return self.graph

    def get_latency_list(self):
        return self.latency_list

    def get_distance_list(self):
        return self.distance_list

    def generate_graph(self, plot=True, g=None):
        # generate a random graph
        if g is None:
            while True:
                g = erdos_renyi_graph(self.num_node, self.link_probability, self.seed)
                if nx.is_connected(g):
                    connectivity = approx.node_connectivity(g)
                    if connectivity > 1:
                        print("Connectivity:" + str(connectivity))
                        print("Min edge cut:" + str(len(nx.minimum_edge_cut(g))))
                        break
                    else:
                        self.seed += 1
                else:
                    self.seed += 1

        self.graph = g

        if plot:
            nx.draw(g, with_labels=True)
            plt.savefig("rg.png")
            plt.clf()

        self.link_property_assign()

        self.graphFunction.set_graph(g)

        self.graphFunction.weight_assign()

        return self.graph

    # set the random bw and latency per link
    def link_property_assign(self):  # Pass in the bw name
        self.latency_list = []
        for (u, v, w) in self.graph.edges(data=True):
            w[Constants.BANDWIDTH] = random.randint(self.low_bw, self.upper_bw)
            w[Constants.ORIGINAL_BANDWIDTH] = w[Constants.BANDWIDTH]
            latency = random.randint(self.low_latency, self.upper_latency)
            w[Constants.LATENCY] = latency
            self.latency_list.append(latency)

        return self.latency_list

    # if u and v connected
    def nodes_connected(self, g, u, v):
        return u in g.neighbors(v)

    def get_connectivity(self):
        con = approx.node_connectivity(self.graph)
        return con


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
