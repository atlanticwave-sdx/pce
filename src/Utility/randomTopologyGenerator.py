    #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  8 13:34:06 2022

@author: yifeiwang
"""
import time
from networkx.generators.random_graphs import erdos_renyi_graph
import networkx as nx
import numpy as np
import random
import operator
import json

import copy

import global_name

class RandomTopologyGenerator:
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

    def grpah(self, g):
        self.graph = g

    def generate_graph(self):
        while True:
            g = erdos_renyi_graph(self.num_node, self.link_probability, self.seed)
            if nx.is_connected(g):
                break
            else:
                seed += 1
        
        self.graph = g

        self.link_property_assign(self)

        return self.graph


    # set the random bw and latency per link
    def link_property_assign(self): ## pass in the bw name
        #latency_list = []
        for (u,v,w) in self.g.edges(data=True):
            w[global_name.bandwidth] = random.randint(self.low_bw,self.upper_bw)
            latency = random.randint(self.low_latency,self.upper_latency) 
            w[global_name.latency] =latency
            #latency_list.append(latency)

        #return latency_list
   
    # set weight (cost) per link, assuming the objective is minizing a function of weight 
    #   flag:
    #       1: bw: weight = alpha*(1.0/bw)
    #       2: latency: weight = latency
    #       2: random: weight = random cost
    #       3: cost: given from outside (static) definition
    #       default: hop: weight =1
    def weightassign(self, flag=1, cost=None):
        random.seed(self.seed)
        distance_list = []

        if flag == 1:
            alpha=10^6
            for (u,v,w) in self.g.edges(data=True):
                w[global_name.weight] = alpha*(1.0/w[global_name.bandwidth])
                distance_list.append(w[global_name.weight])
        elif flag == 2:
            for (u,v,w) in self.g.edges(data=True):
                w[global_name.weight] = w[global_name.latency]
                distance_list.append(w[global_name.weight])
        elif flag == 3:
            for (u,v,w) in self.g.edges(data=True):
                w[global_name.weight] = random.randint(1,2**24)
                distance_list.append(w[global_name.weight])
        elif flag == 4:
            for (u,v,w) in self.g.edges(data=True):
                w[global_name.weight] = cost[u,v] 
                distance_list.append(w[global_name.weight])
        else:
            for (u,v,w) in self.g.edges(data=True):
                w[global_name.weight] = 1.0
                distance_list.append(w[global_name.weight])

        return distance_list

    # if u and v connected
    def nodes_connected(g, u, v):
        return u in g.neighbors(v)

    # return the linked list of link weights associated with a given link list
    def bwlinklist(g,link_list):
        bwlinklist = {}
        for u,v,w in g.edges(data=True):
            bwlinklist[u,v] = w[global_name.bandwidth]

        bwlinkdict = []
        for pair in link_list:
            if (pair[0], pair[1]) in bwlinklist:
                # print("pair"+str((pair[0], pair[1])))
                bw = bwlinklist[(pair[0], pair[1])]
                bwlinkdict.append(bw)
            else:
                bw = bwlinklist[(pair[1], pair[0])]
                bwlinkdict.append(bw)
        #
        with open('./tests/data/bwlinklist.json', 'w') as json_file:
            data = bwlinkdict
            json.dump(data, json_file, indent=4)
        
        return bwlinkdict
    
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

    #
    def latconstraintmaker(self,request_list, latency_list):
        lhs = []
        rhs = []
        #zerolist = self.zerolistmaker(len(latency_list))
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

        with open('./tests/data/latconstraint.json', 'w') as json_file:
            data = latdata
            json.dump(data, json_file, indent=4)

    def GetConnection(self,path):
        with open(path) as f:
            connection = json.load(f)
        return connection

    def lbnxgraphgenerator(self,connection):
        weightassignment = self.weightassign()
        link_dict = {}

        edgelist = list(self.g.edges)

        ## generate each node's parent node
        for pair in self.g.edges:
            if pair[0] in link_dict:
                link_dict[pair[0]].append(pair[1])
            else:
                link_dict[pair[0]]=[pair[1]]
            
            if pair[1] in link_dict:
                link_dict[pair[1]].append(pair[0])
            else:
                link_dict[pair[1]]=[pair[0]]
        linknum = 2*len(self.g.edges)
            
        sorted_dict = dict(sorted(link_dict.items(), key=operator.itemgetter(0)))  
        
        ## show every link (bidirectional link means 2 different link)
        link_list = []
        for startnode in sorted_dict:
            for endnode in sorted_dict[startnode]:
                link_list.append([startnode, endnode])
                
        
        ## generte a link name list for future look up and reference
        linktitle_dict={}
        for n in range(len(link_list)):
            linktitle_dict[n] = link_list[n]

        
        ## create the  constraint matrix of 0s
        nodenum = len(self.g.nodes)    
        inputmatrix = []
        for n in range(nodenum):
            inputmatrix.append(self.zerolistmaker(linknum))

        
        ## input values based on the linklist into the matrix, 1 means flow into the nodes, -1 meanse flow out of the node
        c = 0
        for line in inputmatrix:
            n = 0
            for link in link_list:
                if link[0] == c:
                    inputmatrix[c][n] = -1
                    n= n+1
                elif link[1] == c:
                    inputmatrix[c][n] = 1
                    n=n+1
                else:
                    n=n+1
            c = c+1
        
        
        inputdistance = self.zerolistmaker(len(link_list))
        inputlatency = self.zerolistmaker(len(link_list))
        distance_list = weightassignment[0]
        latency_list = weightassignment[1]


        
        ## look up and form the distance and latency array for each link
        count = 0
        for link in link_list:
            try:
                inputdistance[count] = distance_list[edgelist.index((link[0],link[1]))]
                count = count+1
            except ValueError:
                inputdistance[count] = distance_list[edgelist.index((link[1],link[0]))]
                count = count+1
                
        count = 0        
        for link in link_list:
            try:
                inputlatency[count] = latency_list[edgelist.index((link[0],link[1]))]
                count = count+1
            except ValueError:
                inputlatency[count] = latency_list[edgelist.index((link[1],link[0]))]
                count+=1

        pos = nx.spring_layout(self.g)
        

        with open('./tests/data/latency_list.json', 'w') as json_file:
            data = inputlatency
            json.dump(data, json_file, indent=4)
        

        # Draw the graph according to node positions
        labels = nx.get_edge_attributes(self.g,'bandwidth')
        with open('./tests/data/LB_linklist.json', 'w') as json_file:
            data = link_list
            json.dump(data, json_file,indent=4)

        rhsbw = self.bwlinklist(self.g,link_list)

        with open("./tests/data/latency_list.json") as f:
            latency_list = json.load(f)
        self.latconstraintmaker(connection, latency_list)

        linknum = len(link_list)
        self.jsonfilemaker(self.num_node, inputmatrix, inputdistance, connection,rhsbw, linknum)


        print("Topology Generated!")
        return ("Random Graph is created with " + str(self.num_node) + " nodes, probability of link creation is " + str(self.link_probability))

    def jsonfilemaker(self,nodes, inputmatrix, inputdistance,request_list,rhsbw, linknum):
        bounds = []
        for request in request_list:
            rhs = self.zerolistmaker(nodes)
            rhs[request[0]] = -1
            rhs[request[1]] = 1   
            bounds += rhs

        ## add the bwconstraint rhs
        bounds+=rhsbw

        jsonoutput = {}
        flowconstraints = self.duplicatematrixmaker(request_list,inputmatrix)
        bwconstraints = self.lhsbw(request_list, inputmatrix)

        lhs = flowconstraints + bwconstraints
        cost_list = copy.deepcopy(inputdistance)
        cost = []
        for i in range(len(request_list)):
            cost += cost_list

        with open('./tests/data/latconstraint.json') as f:
            latconstraint = json.load(f)
        lhs+=latconstraint['lhs']
        bounds+=latconstraint['rhs']

        jsonoutput['constraint_coeffs'] = lhs
        jsonoutput['bounds'] = bounds
        jsonoutput['obj_coeffs'] = cost
        jsonoutput['num_vars'] = len(cost)
        jsonoutput['num_constraints'] = len(bounds)
        jsonoutput['num_inequality'] = linknum + int(len(request_list))

        with open('./tests/data/LB_data.json', 'w') as json_file:
            json.dump(jsonoutput, json_file,indent=4)


    def zerolistmaker(self,n):
        listofzeros = [0] * n
        return listofzeros
    # connection = GetConnection('../test/data/test_connection.json')
    # g = GetNetworkToplogy(25,0.4)
    # print(lbnxgraphgenerator(25, 0.4,connection,g))

