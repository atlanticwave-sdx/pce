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
import copy

import Utility.global_name as global_name
from Utility.randomTopologyGenerator import RandomtopologyGenerator

class TE_Solver:
    def __init__(self, g_g = None, tm = None, obj = global_name.Obj_Cost):
        self.graph_generator = g_g 
        self.objective = obj
        self.tm = tm
    
    #form OR matrix
    def create_data_model(self):
        g=self.graph_generator.get_g()

        nodenum = len(g.nodes) 
        linknum = 2*len(g.edges)
        
        #Adjcent matrix
        adj = nx.to_dict_of_lists(g)
        keys=adj.keys()
        links = []
        #list of all links
        for k in keys:
            links = chain(links,zip(cycle([k]),adj[k]))
        
        #flow matrix: 1 means flow into the nodes, -1 meanse flow out of the node
        inputmatrix = np.zeros((nodenum,linknum), dtype=int)
        n=0
        for link in links:
            src=link[0]
            dest=link[1]
            inputmatrix[src][n] = -1
            inputmatrix[n][dest] = 1
        
        #inputdistancelist:link weight
        distance_list=self.graph_generator.get_distance_list()
        latency_list=self.graph_generator.get_latency_list()
        latconstraint = self.latconstraintmaker(self.tm, latency_list)

        #form the bound: rhs
        #flows
        bounds = []
        for request in self.tm:
            rhs = np.zeros(nodenum, dtype=int)
            rhs[request[0]] = -1
            rhs[request[1]] = 1   
            bounds += rhs
        #rhsbw
        bwlinklist = []
        for u,v,w in self.g.edges(data=True):
            bw = w[global_name.bandwidth]
            bwlinklist.append(bw)

        # add the bwconstraint rhs
        bounds+=bwlinklist
        # add the latconstraint rhs
        bounds+=latconstraint['rhs']

        #form the constraints: lhs
        jsonoutput = {}
        flowconstraints = self.duplicatematrixmaker(self.tm,inputmatrix)
        bwconstraints = self.lhsbw(self.tm, inputmatrix)
        lhs = flowconstraints + bwconstraints

        lhs+=latconstraint['lhs']

        #objective functions
        inputdistance = np.zeros(linknum, dtype=int)
        cost_list = copy.deepcopy(inputdistance)
        cost = []
        for i in range(len(self.tm)):
            cost += cost_list

        #form the OR datamodel
        jsonoutput = {}
        jsonoutput['constraint_coeffs'] = lhs
        jsonoutput['bounds'] = bounds
        jsonoutput['num_constraints'] = len(bounds)
        jsonoutput['obj_coeffs'] = cost
        jsonoutput['num_vars'] = len(cost)
        jsonoutput['num_inequality'] = linknum + int(len(self.tm))

    #
    def duplicatematrixmaker(self,request_list,inputmatrix):
        #zeros = self.zerolistmaker(len(inputmatrix[0]))
        zeros = np.zeros(len(inputmatrix[0]))
        outputmatrix = []
        for i in range(len(request_list)):
            for line in inputmatrix:
                outputmatrix.append(zeros * i + line + zeros * (len(request_list)-i-1) )
        return outputmatrix

    #
    def lhsbw(self,request_list, inputmatrix):
        bwconstraints = []
        #zeros = self.zerolistmaker(len(inputmatrix[0])*len(request_list))
        zeros = np.zeros(len(inputmatrix[0])*len(request_list))                  
        for i in range(len(inputmatrix[0])):
            addzeros = copy.deepcopy(zeros)
            bwconstraints.append(addzeros)
            count = 0
            for request in request_list:
                bwconstraints[i][i+count * len(inputmatrix[0])] = request[2]
                count += 1
        return bwconstraints

    def latconstraintmaker(self, request_list, latency_list):
        lhs = []
        rhs = []
        zerolist = np.zeros(len(latency_list))

        requestnum = len(request_list)
        for i in range(requestnum):
            constraint = []
            constraint = i * zerolist + latency_list + (requestnum - 1 - i) * zerolist
            lhs.append(constraint)

        for request in request_list:
            rhs.append(request[3])

        latdata = {}
        latdata["lhs"] = lhs
        latdata["rhs"] = rhs

        #with open('./tests/data/latconstraint.json', 'w') as json_file:
        #    data = latdata
        #    json.dump(data, json_file, indent=4)

        return latdata

    def solve(self):
        pass

    def is_connected(self):
        return nx.is_connected(self.g)
    
    def is_bi_connected(self):
        pass

