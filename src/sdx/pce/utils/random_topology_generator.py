#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  8 13:34:06 2022

@author: Yufeng Xin (yxin@renci.org)
"""
import random

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

    def generate_graph(self, plot=True, g=None) -> nx.Graph:
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
