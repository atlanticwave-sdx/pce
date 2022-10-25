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
from Utility.functions import GraphFunction

class TE_Solver:
    def __init__(self, g = None, tm = None, cost_flag=0, obj = global_name.Obj_Cost):
        self.graph = g

        self.graphFunction = GraphFunction()
        self.graphFunction.set_graph(self.graph)
        self.graphFunction.weight_assign(cost_flag)

        self.objective = obj
        self.tm = tm

        self.links=None #list of links[src][dest], 2*numEdges 

    def solve(self):
        data = self.create_data_model()
        
        num_inequality = data['num_inequality']

        # Create the mip solver with the SCIP backend.
        solver = pywraplp.Solver.CreateSolver('SCIP')


        x = {}
        for j in range(data['num_vars']):
            x[j] = solver.IntVar(0, 1, 'x[%i]' % j)
        print('Number of variables =', solver.NumVariables())
        print('num_constraints:', data['num_constraints'])
        print('num_inequality', num_inequality)

        for i in range(data['num_constraints']-num_inequality):
            constraint_expr = [data['constraint_coeffs'][i][j] * x[j] for j in range(data['num_vars'])]
            solver.Add(sum(constraint_expr) == data['bounds'][i])
        
        print(len(data['bounds']))
        #print(data['bounds'])
        print(len(data['constraint_coeffs']))
        #print(data['constraint_coeffs'])
        print(num_inequality)
        
        for i in range(data['num_constraints'] - num_inequality, data['num_constraints']):
            constraint_expr = [data['constraint_coeffs'][i][j] * x[j] for j in range(data['num_vars'])]
            solver.Add(sum(constraint_expr) <= data['bounds'][i])   
        print('Number of constraints =', solver.NumConstraints())


        objective = solver.Objective()
        for j in range(data['num_vars']):
            objective.SetCoefficient(x[j], data['obj_coeffs'][j])
        objective.SetMinimization()

        status = solver.Solve()
        solution = []
        path=None
        if status == pywraplp.Solver.OPTIMAL:
            print('Objective value =', solver.Objective().Value())
            for j in range(data['num_vars']):
                # print(x[j].name(), ' = ', x[j].solution_value())
                solution.append(x[j].solution_value())
            
            path = np.array(solution).reshape(len(self.tm),-1)
            print(path.shape)
            #print(path)

            # print('Problem solved in %f milliseconds' % solver.wall_time())
            # print('Problem solved in %d iterations' % solver.iterations())
            # print('Problem solved in %d branch-and-bound nodes' % solver.nodes())
        else:
            print('The problem does not have an optimal solution.')
        
        return path, solver.Objective().Value()

    def solution_translator(self,paths,solution):
        #extract the edge/path
        real_paths=[]
        for path in paths:
            real_path=[]
            i=0
            for edge in path:
                if abs(edge - 1) < 0.001: # =1: edge on the path
                    real_path.append(self.links[i])
                i=i+1
            real_paths.append(real_path)

        #associate with the TM requests
        id_connection=0
        ordered_paths={}
        for connection in self.tm:
            src=connection[0]
            dest=connection[1]
            bw=connection[2]
            latency=connection[3]
            ordered_path=[]
            ordered_paths[(src,dest,bw)] = ordered_path
            #print("src:"+str(src)+"-dest:"+str(dest))
            path = real_paths[id_connection]
            i=0
            while src != dest and i<10:
                for edge in path:
                    #print("edge:"+str(edge))
                    if edge[0] == src:
                        ordered_path.append(edge)
                        src=edge[1]
                        break
                    #if src==dest:
                    #    print("ordered the path:"+str(src) +":"+str(dest)+":"+str(i)+";"+str(ordered_path))
                    #    break
                i=i+1
            id_connection=id_connection+1
        #print("ordered paths:"+str(ordered_paths))
        return ordered_paths

    def update_graph(self,graph,paths):
        for connection, path in paths.items():
            
            src=connection[0]
            dest=connection[1]
            bw=connection[2]

            for edge in path:
                u=edge[0]
                v=edge[1]
                if graph.has_edge(u,v):
                    bandwidth = graph[u][v][global_name.bandwidth] - bw
                    graph[u][v][global_name.bandwidth] = max(bandwidth,0)
        return graph

    def set_obj(self,obj):
        self.objective = obj
    
    #form OR matrix
    def mc_cost(self,links):
        g=self.graph
        cost_list=[]
        for link in links:
            cost_list.append(g[link[0]][link[1]][global_name.weight])

        cost = []
        for i in range(len(self.tm)):
            cost += cost_list
        
        return cost

    def lb_cost(self,links):
        g=self.graph
        cost_list=[]
        for link in links:
            cost_list.append(g[link[0]][link[1]][global_name.bandwidth])
        cost = []
        for connection in self.tm:
            bw=connection[2]
            #cost += cost_list       
            cost+=[bw/link for link in cost_list]

        return cost

    def create_data_model(self):
        g=self.graph

        nodenum = g.number_of_nodes()
        linknum = g.number_of_edges()

        print("\n #Nodes:" + str(nodenum))
        print("\n #Links:" + str(linknum))

        #graph flow matrix
        inputmatrix,links = self.flow_matrix(g)
        self.links=links
        #inputdistancelist:link weight
        #distance_list=self.graph_generator.get_distance_list()
        #latency_list=self.graph_generator.get_latency_list()

        #print("distance_list:"+str(np.shape(distance_list)))        
        #print("latency_list:"+str(np.shape(latency_list)))

        latconstraint = self.latconstraintmaker(links)

        #form the bound: rhs
        #flows: numnode*len(request)
        bounds = []
        for request in self.tm:
            rhs = np.zeros(nodenum, dtype=int)
            rhs[request[0]] = -1
            rhs[request[1]] = 1   
            bounds+=list(rhs)

        print("bound 1:"+str(len(bounds)))

        #rhsbw -TODO *2 edges
        bwlinklist = []
        for link in links:
            u=link[0]
            v=link[1]
            if g.has_edge(u,v):
                bw = g[u][v][global_name.bandwidth]
            elif g.has_edge(v,u):
                bw = g[v][u][global_name.bandwidth]

            bwlinklist.append(bw)

        # add the bwconstraint rhs
        bounds+=bwlinklist
        print("bound 2:"+str(len(bounds)))

        # add the latconstraint rhs
        bounds+=latconstraint['rhs']
        print("bound 3:"+str(len(bounds)))
        #print(bounds)

        #form the constraints: lhs
        flowconstraints = self.lhsflow(self.tm,inputmatrix)
        bwconstraints = self.lhsbw(self.tm, inputmatrix)

        print("\nConstraints Shape:"+str(len(flowconstraints))+":"+str(len(bwconstraints)))
        #print("\n flow"+str(flowconstraints))
        #print("\n bw:"+str(type(bwconstraints)))

        bw_np = np.array(bwconstraints)
        print("np:"+str(flowconstraints.shape)+":"+str(bw_np.shape))
        flow_lhs = np.concatenate((flowconstraints,bw_np))
        print("flow_lhs:"+str(np.shape(flow_lhs)))
        print("latcons:"+str(np.shape(latconstraint['lhs'])))

        lhs=np.concatenate((flow_lhs,latconstraint['lhs']))

        #objective function
        if self.objective == global_name.Obj_Cost:
            print("Objecive: Cost")
            cost=self.mc_cost(links)
        if self.objective == global_name.Obj_LB:
            print("Objecive: Load Balance")
            cost=self.lb_cost(links)

        print("cost len:"+str(len(cost)))
        #print(cost)
        print("lhs shape:"+str(lhs.shape))
        print("rhs shape:"+str(len(bounds)))

        coeffs=[]
        for i in range(lhs.shape[0]):
            row = list(lhs[i])
            coeffs.append(row)

        #form the OR datamodel
        jsonoutput = {}
        jsonoutput['constraint_coeffs'] = coeffs
        jsonoutput['bounds'] = list(bounds)
        jsonoutput['num_constraints'] = len(bounds)
        jsonoutput['obj_coeffs'] = list(cost)
        jsonoutput['num_vars'] = len(cost)
        jsonoutput['num_inequality'] = 2*linknum + int(len(self.tm))

        return jsonoutput

    #flowmatrix
    #also set self.links: 2*links
    def flow_matrix(self, g):
        nodenum = len(g.nodes) 
        linknum = 2*len(g.edges)
        
        #Adjcent matrix, key:node; value:list of neighboring nodes
        adj = nx.to_dict_of_lists(g)

        keys=adj.keys()
        links = []
        #list of all links

        for k in keys:
            links = chain(links,zip(cycle([k]),adj[k]))
        
        #list of links directional: tuple (src,nei), len =2*#edges
        link_list = list(links)
        #print(link_list)

        #flow matrix: 1 means flow into the nodes, -1 meanse flow out of the node
        inputmatrix = np.zeros((nodenum,linknum), dtype=int)
        n=0
        for link in link_list:
            src=link[0]
            dest=link[1]
            #print(str(src)+":"+str(dest)+"\n")
            inputmatrix[src][n] = -1
            inputmatrix[dest][n] = 1
            n+=1

        return inputmatrix,link_list

    #shape: (len(tm)*numnode, len(num)*2*numedge)
    def lhsflow(self,request_list,inputmatrix):
        r = len(request_list)
        m,n = inputmatrix.shape
        print("r="+str(r)+":m="+str(m)+":n="+str(n))
        #out = np.zeros((r,m,r,n), dtype=inputmatrix.dtype)
        #diag = np.einsum('ijik->ijk',out)
        #diag[:] = inputmatrix
        #print("diag:" + str(diag.shape))
        #return diag.reshape(m*r,n*r)
        #print(inputmatrix)
        out = np.zeros((r*m,r*n), dtype=inputmatrix.dtype)
        for i in range(r):
            out[i*m:(i+1)*m,i*n:(i+1)*n]=inputmatrix
        print("out:"+str(out.shape))
        return out
    #
    def lhsbw(self,request_list, inputmatrix):
        bwconstraints = []
        #zeros = self.zerolistmaker(len(inputmatrix[0])*len(request_list))
        zeros = np.zeros(len(inputmatrix[0])*len(request_list),dtype=int)                  
        for i in range(len(inputmatrix[0])):
            addzeros = copy.deepcopy(zeros)
            bwconstraints.append(addzeros)
            count = 0
            for request in request_list:
                bwconstraints[i][i+count * len(inputmatrix[0])] = request[2]
                count += 1

        return bwconstraints

    def latconstraintmaker(self, links):
        lhs = []
        rhs = []

        request_list = self.tm
        print("request:"+str(len(request_list)))
        print("links:"+str(len(links)))

        g=self.graph
        zerolist = np.zeros(len(links),dtype=int)
        latency_list=[]
        for link in links:
            latency_list.append(g[link[0]][link[1]][global_name.latency])

        requestnum = len(request_list)
        for i in range(requestnum):
            constraint = []
            constraint = i*zerolist.tolist() + latency_list + (requestnum - 1 - i) * zerolist.tolist()
            #print("constraint:"+str(len(constraint)))
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

