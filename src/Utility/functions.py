# -*- coding: utf-8 -*-
"""
Created on Wed Aug 11 16:40:56 2021

@author: Yufeng Xin (yxin@renci.org)
"""

import networkx as nx
from networkx.algorithms import approximation as approx
import random

import Utility.global_name as global_name

class GraphFunction():
    def __init__(self, g = None)  -> None:
        self.graph = g

    def dijsktra(self,u,v):
        pass

    def backup(self, u, v):
        pass

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

    def biconnectivity(self):
        pass


def create_unvisited_list(link_list):
    unvisited_list=[]
    for keys in link_list:
        unvisited_list.append(keys)
    return unvisited_list

def create_unvisited_node(my_list):
    unvisited_node={}
    for keys in my_list:
         unvisited_node[keys]=0
    return  unvisited_node
        
def get_graph_info(link_list):
    key_list=[]
    for keys in link_list:
        key_list.append()
    print(key_list)
