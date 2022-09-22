    #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  8 13:34:06 2022

@author: yifeiwang
"""
import time
from networkx.generators.random_graphs import erdos_renyi_graph
from networkx.algorithms import approximation as approx
import networkx as nx
import numpy as np
import random
import operator
import json

import copy

import Utility.global_name as global_name

class RandomTopologyGenerator():
    # inputs:
    #   N: Total number of the random network's nodes
    #   P: link creation probability
    def __init__(self, N, P, l_bw= 2000, u_bw=3000, l_lat =1, u_lat=10, seed=2022):
        random.seed(seed)
        self.seed=seed

        self.num_node = N  
        self.link_probability = P

        self.low_bw = l_bw
        self.upper_bw = u_bw
        self.low_latency = l_lat   
        self.upper_latency = u_lat 

    def bw_range(self, l_bw, u_bw):
        self.low_bw = l_bw   
        self.upper_bw = u_bw   

    def latency_range(self, l_lat, u_lat):
        self.low_latency = l_lat   
        self.upper_latency = u_lat 

    def graph(self, g):
        self.graph = g

    def get_graph(self):
        return self.graph

    def get_latency_list(self):
        return self.latency_list

    def get_distance_list(self):
        return self.distance_list

    def generate_graph(self,g=None):
        #generate a random graph
        if g is None:
            while True:
                g = erdos_renyi_graph(self.num_node, self.link_probability, self.seed)
                if nx.is_connected(g):
                    break
                else:
                    seed += 1
        
        self.graph = g

        self.link_property_assign()
        self.weight_assign()

        return self.graph


    # set the random bw and latency per link
    def link_property_assign(self): ## pass in the bw name
        self.latency_list = []
        for (u,v,w) in self.graph.edges(data=True):
            w[global_name.bandwidth] = random.randint(self.low_bw,self.upper_bw)
            latency = random.randint(self.low_latency,self.upper_latency) 
            w[global_name.latency] =latency
            self.latency_list.append(latency)

        return self.latency_list
   
    # set weight (cost) per link, assuming the objective is minizing a function of weight 
    #   flag:
    #       1: bw: weight = alpha*(1.0/bw)
    #       2: latency: weight = latency
    #       2: random: weight = random cost
    #       3: cost: given from outside (static) definition
    #       default: hop: weight =1
    def weight_assign(self, flag=1, cost=None):
        random.seed(self.seed)
        distance_list = []

        if flag == 1:
            alpha=10^6
            for (u,v,w) in self.graph.edges(data=True):
                w[global_name.weight] = alpha*(1.0/w[global_name.bandwidth])
                distance_list.append(w[global_name.weight])
        elif flag == 2:
            for (u,v,w) in self.graph.edges(data=True):
                w[global_name.weight] = w[global_name.latency]
                distance_list.append(w[global_name.weight])
        elif flag == 3:
            for (u,v,w) in self.graph.edges(data=True):
                w[global_name.weight] = random.randint(1,2**24)
                distance_list.append(w[global_name.weight])
        elif flag == 4:
            for (u,v,w) in self.graph.edges(data=True):
                w[global_name.weight] = cost[u,v] 
                distance_list.append(w[global_name.weight])
        else:
            for (u,v,w) in self.graph.edges(data=True):
                w[global_name.weight] = 1.0
                distance_list.append(w[global_name.weight])
        self.distance_list = distance_list
        return distance_list

    # if u and v connected
    def nodes_connected(g, u, v):
        return u in g.neighbors(v)

    def get_connectivity(self):
        con=approx.node_connectivity(self.graph)
        return con

    # connection = GetConnection('../test/data/test_connection.json')
    # g = GetNetworkToplogy(25,0.4)
    # print(lbnxgraphgenerator(25, 0.4,connection,g))

