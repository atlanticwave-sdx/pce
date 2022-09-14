#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep  7 13:42:31 2022

@author: Yufeng Xin (RENCI)
"""

from ortools.linear_solver import pywraplp
import networkx as nx
import numpy as np

from itertools import cycle
from itertools import chain

import json

import Utility.global_name as global_name

class TE_Solver:
    def __init__(self, g = None, tm = None, obj = global_name.Obj_Cost):
        self.graph = g
        self.objective = obj
        self.connection = tm

    def create_data_model(self):
        nodenum = len(self.g.nodes) 
        linknum = 2*len(self.g.edges)

        adj = nx.to_dict_of_lists(self.g)
        keys=adj.keys()
        links = []
        for k in keys:
            links = chain(m,zip(cycle([k]),adj[k]))
        
        inputmatrix = np.zeros((nodenum,linknum), dtype=int)
        n=0
        for link in links:
            src=link[0]
            dest=link[1]
            inputmatrix[src][n] = -1
            inputmatrix[n][dest] = 1


    def solve(self):
        pass

    def is_connected(self):
        return nx.is_connected(self.g)
    
    def is_bi_connected(self):
        pass

