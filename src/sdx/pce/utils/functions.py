# -*- coding: utf-8 -*-
"""
Created on Wed Aug 11 16:40:56 2021

@author: Yufeng Xin (yxin@renci.org)
"""

import copy
import random

from networkx.algorithms import approximation as approx

from sdx.pce.utils.constants import Constants


class GraphFunction:
    def __init__(self, g=None) -> None:
        self.graph = g

    def set_graph(self, g=None):
        self.graph = g

    def weight_assign(self, cost_flag=Constants.COST_FLAG_HOP, cost=None):
        """
        Set weight (cost) per link.

        The assumption is that the objective is minizing a function of
        weight.

        :param cost_flag: a constant defined in constants.py, whose
            possible values are:

                - COST_FLAG_BW : weight = alpha*(1.0/bw)

                - COST_FLAG_LATENCY: weight = latency

                - COST_FLAG_RANDOM: weight = random cost

                - COST_FLAG_STATIC: given from outside (static)
                  definition

                - COST_FLAG_HOP (the defaul): hop: weight = 1
        """
        distance_list = []

        if cost_flag == Constants.COST_FLAG_BW:
            for u, v, w in self.graph.edges(data=True):
                # w[Constants.WEIGHT] = Constants.Max_L_BW - w[Constants.BANDWIDTH]
                w[Constants.WEIGHT] = Constants.ALPHA * (1.0 / w[Constants.BANDWIDTH])
                distance_list.append(w[Constants.WEIGHT])
        elif cost_flag == Constants.COST_FLAG_LATENCY:
            for u, v, w in self.graph.edges(data=True):
                w[Constants.WEIGHT] = w[Constants.LATENCY]
                distance_list.append(w[Constants.WEIGHT])
        elif cost_flag == Constants.COST_FLAG_RANDOM:
            for u, v, w in self.graph.edges(data=True):
                w[Constants.WEIGHT] = random.randint(1, 2**24)
                distance_list.append(w[Constants.WEIGHT])
        elif cost_flag == Constants.COST_FLAG_STATIC:
            for u, v, w in self.graph.edges(data=True):
                w[Constants.WEIGHT] = cost[u, v]
                distance_list.append(w[Constants.WEIGHT])
        else:
            for u, v, w in self.graph.edges(data=True):
                w[Constants.WEIGHT] = 1.0
                distance_list.append(w[Constants.WEIGHT])
        self.distance_list = distance_list
        return distance_list

    # if u and v connected
    def nodes_connected(self, g, u, v):
        return u in g.neighbors(v)

    def get_connectivity(self):
        con = approx.node_connectivity(self.graph)
        return con

    def biconnectivity(self):
        pass


""" use dijsktra to get the primary shortest path """
def dijnew(graph, start_node, end_node):
    graph_new = graph_simplify(graph)
    shortest_distance = {}
    predecessor = {}
    unseen_nodes = graph_new
    infinity = 9999999
    path = []
    for node in unseen_nodes:
        shortest_distance[node] = infinity
    shortest_distance[start_node] = 0

    while unseen_nodes:  # loop all the nodes in the list
        min_node = None
        for node in unseen_nodes:
            if min_node is None:
                min_node = node
            elif shortest_distance[node] < shortest_distance[min_node]:
                min_node = node  # find the current node

        for child_node, weight in graph[min_node].items():
            if weight + shortest_distance[min_node] < shortest_distance[child_node]:
                shortest_distance[child_node] = weight + shortest_distance[min_node]
                predecessor[child_node] = min_node
        unseen_nodes.pop(min_node)

    current_node = end_node  # run path backwards to get the real path
    while current_node != start_node:
        try:
            path.insert(0, current_node)
            current_node = predecessor[current_node]
        except KeyError:
            print("Path not reachable")
            break
    path.insert(0, start_node)
    if (
        shortest_distance[end_node] != infinity
    ):  # check if the end_node has been reached
        print("Shortest distance is " + str(shortest_distance[end_node]))
        print("And the path is " + str(path))
    return path


""" make the non-simple graph to be the simple graph """
def graph_simplify(graph):
    for node in graph:
        for endpoint in graph[node]:
            try:
                if len(graph[node][endpoint]) > 1:
                    shortest = min(graph[node][endpoint])
                    graph[node][endpoint] = shortest
            except TypeError:
                pass
    return graph


""" remove the primary shortest path and redo the dijsktra to get the backup path """
def backup_path(graph, start_node, end_node):
    backupstart_node = start_node
    backupend_node = end_node
    graphprimary = copy.deepcopy(graph)
    graph_original = copy.deepcopy(graph)
    graph_new = graph_simplify(graph)
    print("The primary path: ")
    path = dijnew(graphprimary, start_node, end_node)
    path_new = path.copy()
    path_new.pop()

    for (
        ele
    ) in path_new:  # update the graph, delete the path that was used in primary path
        index = path.index(ele)
        try:
            graph_original[ele][path[index + 1]].remove(graph_new[ele][path[index + 1]])
        except AttributeError:
            del graph_original[ele][path[index + 1]]

    for start_node in graph_original:  # reformat the updated graph list
        for end_node in graph_original[start_node]:
            try:
                if len(graph_original[start_node][end_node]) == 1:
                    graph_original[start_node][end_node] = graph_original[start_node][
                        end_node
                    ][0]
            except TypeError:
                continue

    print("The back up path: ")
    dijnew(graph_original, backupstart_node, backupend_node)


def create_unvisited_list(link_list):
    unvisited_list = []
    for keys in link_list:
        unvisited_list.append(keys)
    return unvisited_list


def create_unvisited_node(my_list):
    unvisited_node = {}
    for keys in my_list:
        unvisited_node[keys] = 0
    return unvisited_node


def get_graph_info(link_list):
    key_list = []
    for keys in link_list:
        key_list.append()
    print(key_list)
