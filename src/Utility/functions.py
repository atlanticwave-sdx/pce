# -*- coding: utf-8 -*-
"""
Created on Wed Aug 11 16:40:56 2021

@author: Yufeng Xin (yxin@renci.org)
"""

import copy
import random

from networkx.algorithms import approximation as approx

import Utility.global_name as global_name


class GraphFunction:
    def __init__(self, g=None) -> None:
        self.graph = g

    def set_graph(self, g=None):
        self.graph = g

    # set weight (cost) per link, assuming the objective is minizing a function of weight
    #   flag:
    #       1: bw: weight = alpha*(1.0/bw)
    #       2: latency: weight = latency
    #       3: random: weight = random cost
    #       4: cost: given from outside (static) definition
    #       0 and default: hop: weight =1
    def weight_assign(self, flag=0, cost=None):

        distance_list = []

        if flag == 1:
            for (u, v, w) in self.graph.edges(data=True):
                # w[global_name.weight] = global_name.Max_L_BW - w[global_name.bandwidth]
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

    def biconnectivity(self):
        pass


# use dijsktra to get the primary shortest path
def dijnew(graph, start_node, end_node):
    graph_new = graph_simplify(graph)
    shortest_distance = {}
    predecessor = {}
    unseenNodes = graph_new
    infinity = 9999999
    path = []
    for node in unseenNodes:
        shortest_distance[node] = infinity
    shortest_distance[start_node] = 0

    while unseenNodes:  # loop all the nodes in the list
        minNode = None
        for node in unseenNodes:
            if minNode is None:
                minNode = node
            elif shortest_distance[node] < shortest_distance[minNode]:
                minNode = node  # find the current node

        for childNode, weight in graph[minNode].items():
            if weight + shortest_distance[minNode] < shortest_distance[childNode]:
                shortest_distance[childNode] = weight + shortest_distance[minNode]
                predecessor[childNode] = minNode
        unseenNodes.pop(minNode)

    currentNode = end_node  # run path backwards to get the real path
    while currentNode != start_node:
        try:
            path.insert(0, currentNode)
            currentNode = predecessor[currentNode]
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


# make the non-simple graph to be the simple graph
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


# remove the primary shortest path and redo the dijsktra to get the backup path
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
