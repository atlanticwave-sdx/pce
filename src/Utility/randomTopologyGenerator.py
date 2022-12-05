#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  8 13:34:06 2022

@author: Yufeng Xin (yxin@renci.org)
"""
import copy
import json
import operator
import random
import re
import time

import networkx as nx
import numpy as np
import pylab as plt
from networkx.algorithms import approximation as approx
from networkx.generators.random_graphs import erdos_renyi_graph

import Utility.global_name as global_name
from Utility.functions import GraphFunction


class RandomTopologyGenerator:
    # inputs:
    #   N: Total number of the random network's nodes
    #   P: link creation probability
    def __init__(
        self,
        N,
        P=0.2,
        l_bw=global_name.Min_L_BW,
        u_bw=global_name.Max_L_BW,
        l_lat=global_name.Min_L_LAT,
        u_lat=global_name.Max_L_LAT,
        seed=2022,
    ):
        random.seed(seed)
        self.seed = seed

        self.num_node = N
        self.link_probability = P

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
            w[global_name.bandwidth] = random.randint(self.low_bw, self.upper_bw)
            w[global_name.original_bandwidth] = w[global_name.bandwidth]
            latency = random.randint(self.low_latency, self.upper_latency)
            w[global_name.latency] = latency
            self.latency_list.append(latency)

        return self.latency_list

    # set weight (cost) per link, assuming the objective is minizing a function of weight
    #   flag:
    #       1: bw: weight = alpha*(1.0/bw)
    #       2: latency: weight = latency
    #       2: random: weight = random cost
    #       3: cost: given from outside (static) definition
    #       default: hop: weight =1
    def weight_assign(self, flag=5, cost=None):
        random.seed(self.seed)
        distance_list = []

        if flag == 1:
            for (u, v, w) in self.graph.edges(data=True):
                w[global_name.weight] = global_name.alpha * (
                    1.0 / w[global_name.bandwidth]
                )
                distance_list.append(w[global_name.weight])
        elif flag == 2:
            for (u, v, w) in self.graph.edges(data=True):
                w[global_name.weight] = w[global_name.latency]
                distance_list.append(w[global_name.weight])
        elif flag == 3:
            for (u, v, w) in self.graph.edges(data=True):
                w[global_name.weight] = random.randint(1, 2**24)
                distance_list.append(w[global_name.weight])
        elif flag == 4:
            for (u, v, w) in self.graph.edges(data=True):
                w[global_name.weight] = cost[u, v]
                distance_list.append(w[global_name.weight])
        else:
            for (u, v, w) in self.graph.edges(data=True):
                w[global_name.weight] = 1.0
                distance_list.append(w[global_name.weight])
        self.distance_list = distance_list
        return distance_list

    # if u and v connected
    def nodes_connected(g, u, v):
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

        w[global_name.original_bandwidth] = float(bandwidth)
        w[global_name.bandwidth] = float(bandwidth)
        w[global_name.weight] = float(w["cost"])
        if "latency" not in w.keys():
            latency = 10
            w[global_name.latency] = latency

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
