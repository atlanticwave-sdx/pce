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

class TE_Solver:
    def __init__(self, g_g = None, tm = None, obj = global_name.Obj_Cost):
        self.graph_generator = g_g 
        self.objective = obj
        self.tm = tm

    def solve(self):
        data = self.create_data_model()
        
        num_inequality = data['num_inequality']

        # Create the mip solver with the SCIP backend.
        solver = pywraplp.Solver.CreateSolver('SCIP')


        x = {}
        for j in range(data['num_vars']):
            x[j] = solver.IntVar(0, 1, 'x[%i]' % j)
        print('Number of variables =', solver.NumVariables())


        for i in range(data['num_constraints']-num_inequality):
            constraint_expr = [data['constraint_coeffs'][i][j] * x[j] for j in range(data['num_vars'])]
            solver.Add(sum(constraint_expr) == data['bounds'][i])
        for i in range(data['num_constraints']-num_inequality, data['num_constraints']):
            constraint_expr = [data['constraint_coeffs'][i][j] * x[j] for j in range(data['num_vars'])]
            solver.Add(sum(constraint_expr) <= data['bounds'][i])     
        print('Number of constraints =', solver.NumConstraints())

        objective = solver.Objective()
        for j in range(data['num_vars']):
            objective.SetCoefficient(x[j], data['obj_coeffs'][j])
        objective.SetMinimization()

        status = solver.Solve()
        solution = []

        if status == pywraplp.Solver.OPTIMAL:
            print('Objective value =', solver.Objective().Value())
            for j in range(data['num_vars']):
                # print(x[j].name(), ' = ', x[j].solution_value())
                solution.append(x[j].solution_value())
            print()
            # print('Problem solved in %f milliseconds' % solver.wall_time())
            # print('Problem solved in %d iterations' % solver.iterations())
            # print('Problem solved in %d branch-and-bound nodes' % solver.nodes())
        else:
            print('The problem does not have an optimal solution.')
        
        return solution, solver.Objective().Value()

    def set_obj(self,obj):
        self.objective = obj
    
    #form OR matrix
    def mc_cost(self,inputdistance):
        cost_list = copy.deepcopy(inputdistance)
        cost = []
        for i in range(len(self.tm)):
            cost += cost_list

    def lb_cost(self,inputdistance):
        cost_list = copy.deepcopy(inputdistance)
        cost = []
        for connection in range(len(self.tm)):
            bw=connection[2]
            cost += cost_list       
            cost+=[bw/link for link in cost_list]

    def create_data_model(self):
        g=self.graph_generator.get_graph()

        nodenum = g.number_of_nodes()
        linknum = g.number_of_edges()

        #graph flow matrix
        inputmatrix= self.flow_matrix(g)
        
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
        for u,v,w in g.edges(data=True):
            bw = w[global_name.bandwidth]
            bwlinklist.append(bw)

        # add the bwconstraint rhs
        bounds+=bwlinklist
        # add the latconstraint rhs
        bounds+=latconstraint['rhs']

        #form the constraints: lhs
        jsonoutput = {}
        flowconstraints = self.lhsflow(self.tm,inputmatrix)
        bwconstraints = self.lhsbw(self.tm, inputmatrix)
        lhs = flowconstraints + bwconstraints

        lhs+=latconstraint['lhs']

        #objective function
        if self.objective == global_name.Obj_Cost:
            cost=self.mc_cost(distance_list)
        if self.objective == global_name.Obj_LB:
            cost=self.lb_cost(distance_list)

        #form the OR datamodel
        jsonoutput = {}
        jsonoutput['constraint_coeffs'] = lhs
        jsonoutput['bounds'] = bounds
        jsonoutput['num_constraints'] = len(bounds)
        jsonoutput['obj_coeffs'] = cost
        jsonoutput['num_vars'] = len(cost)
        jsonoutput['num_inequality'] = linknum + int(len(self.tm))

        return jsonoutput

    #flowmatrix
    def flow_matrix(self, g):
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

        return inputmatrix

    #
    def lhsflow(self,request_list,inputmatrix):
        r = len(request_list)
        m,n = inputmatrix.shape
        out = np.zeros((r,m,r,n), dtype=inputmatrix.dtype)
        diag = np.einsum('ijik->ijk',out)
        diag[:] = inputmatrix
        return out.reshape(-1,n*r)

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

    def is_connected(self):
        return nx.is_connected(self.g)
    
    def is_bi_connected(self):
        pass

