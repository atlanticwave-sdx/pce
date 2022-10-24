import argparse
import json
import numpy as np

from LoadBalancing.MC_Solver import runMC_Solver
from LoadBalancing.RandomTopologyGenerator import lbnxgraphgenerator
from LoadBalancing.RandomTopologyGenerator import GetNetworkToplogy

import Utility.global_name as global_name
from Utility.randomTopologyGenerator import RandomTopologyGenerator
from Utility.randomConnectionGenerator import RandomConnectionGenerator

from LoadBalancing.TE_Solver import TE_Solver

def random_graph(n, p, m):
 
    graph_generator = RandomTopologyGenerator(n, p)
    graph=graph_generator.generate_graph()

    tm_generator = RandomConnectionGenerator(n)
    tm = tm_generator.randomConnectionGenerator(m, 500, 2000, 50, 80)

    return graph,tm

class TE_Group_Solver():
    """"
    Class for a connection (TE matrix) splitting based heuristic 
    1. Sequential: binpacking like heuristic: first-fit(any-fit)-decreasing, refined first fit (4 classes): Online
    2. Grouping: k-shortest-path based grouping: (k, then all other pairs sharing a same link) : 
        connection grouping: linear grouping (k largest items on); geometric grouping (interval [B/2^(r+1), B/2^2])  
    """

    def __init__(self, topology, tm, cost, objective):
        self.tm = tm
        self.topology = topology
        self.cost = cost
        self.objective = objective
        self.pad=0

    def ConnectionSplit(self,s, k):
        s_tm=self.sort_tm()
        if s==0:
            partition_tm=self.linear_partition(s_tm,k)
        if s==1:
            partition_tm=self.geometry_partition()
        if s==2:
            partition_tm=self.alt_partition()
        
        return partition_tm

    def sort_tm(self):
        #sorted_tm = np.sort(np.asarray(self.tm), axis = -1)
        print("tm shape:"+str(np.shape(self.tm)))
        #dtype = ('src', int),('dest', int), ('bandwidth', float), ('latency', float)
        dtype = {'names':['src', 'dest', 'bandwidth', 'latency'], 'formats':[int, int, float, float]}
        np_tm= np.array(self.tm,dtype=dtype)
        #sorted_tm = np_tm[np_tm[:,2].argsort()]
        sorted_tm = np.sort(np_tm, order='bandwidth')
        print(sorted_tm)
        return sorted_tm
    
    def linear_partition(self, sorted_tm, k):
        partition_tm=[]
        num_connection = sorted_tm.shape[0]
        num, mod = divmod(num_connection,k)
        #print(sorted_tm)

        if mod !=0:
            dtype = {'names':['src', 'dest', 'bandwidth', 'latency'], 'formats':[int, int, float, float]}
            self.pad=k-mod
            pad_zeros = np.zeros((self.pad,),dtype=dtype)
            #print(pad_zeros)
            #print(type(pad_zeros))
            #print(sorted_tm.shape)
            partition = sorted_tm[0:mod-1]
            sorted_tm = np.append(pad_zeros,sorted_tm, axis=0)
            num=num+1
        for i in range(0, num_connection+mod, num):
            partition = sorted_tm[i:i+num]
            partition_tm.append(partition) 
        print("Linear tm partitioning:"+str(k)+":"+str(num)+":"+str(mod)+":shape="+str(np.shape(partition_tm)))
        #
        return partition_tm

    def geometry_partition(self):
        pass

    def alt_partition(self):
        pass
    
    def solve(self, partition_tm):
        partition_shape = np.shape(partition_tm)
        graph = self.topology
        for i in range(partition_shape[0]-1,-1,-1):
            #print("i="+str(i))
            if i==0:
                partition=partition_tm[i][self.pad:]
            else:
                partition=partition_tm[i] 
            print(partition)
            solver = TE_Solver(graph, partition, self.cost, self.objective)
            path,result = solver.solve()
            ordered_paths = solver.solution_translator(path,result)
            graph=solver.update_graph(graph,ordered_paths)

    def Heuristic_CSP(self,connection,g):
        self.ConnectionSplit(connection)
        pathlist = {}
        cost = 0
        c = 1
        with open('./tests/data/splittedconnection.json') as f:
            connection= json.load(f)
        for query in connection:
            singleconnection = [query]
            with open('./tests/data/connection.json', 'w') as json_file:
                data = singleconnection
                json.dump(data, json_file, indent=4)

            lbnxgraphgenerator(25, 0.4,data, g)

            solution = runMC_Solver()
            pathlist[str(c)]=solution[0]["1"]
            cost += solution[1]
            c+=1

        return[pathlist,cost]

if __name__ == '__main__':

    parse = argparse.ArgumentParser()
    parse.add_argument('-t', dest='te_file', required=False, help='Input file for the connections or traiffc matrix, e.g. c connection.json. Required.', type=str)
    parse.add_argument('-n', dest='topology_file', required=False, help='Input file for the network topology, e.g. t topology.json. Required.', type=str)
    parse.add_argument('-c', dest='c', required=False, default=0, help='Link cost definition', type=int)
    parse.add_argument('-b', dest='b', required=False, default=0, help='Objective: MinCost or Load balancing', type=int)
    parse.add_argument('-m', dest='m', required=False, help='Number of connections in the random TE', type=int)
    parse.add_argument('-a', dest='alg', default=0, help='Flag for different grouping heuristic algorithms, default is the linear partition', type=int)
    parse.add_argument('-g', dest='group', default=2, help='number of groups', type=int)
    parse.add_argument('-o' , dest='result', default='OUTPUT.txt', help='Output file, e.g. o result.txt. If this option is not given, assume standard output.', type=str)

    parse.print_help()
    args = parse.parse_args()
    #result(args.te_file,args.node_name , args.result)

    if args.topology_file is not None:
        if args.te_file is not None:
            graph, tm = dot_file(args.topology_file,args.te_file)
        else:
            print("Missing the TE file!")
            exit()    
    else:
        n=25
        p=0.2
        if args.m is None:
            print("Using default:"+"m=3")
            args.m = 3

        graph, tm = random_graph(n,p,args.m)

    te = TE_Group_Solver(graph, tm, args.c, args.b)
    partition_tm = te.ConnectionSplit(args.alg, args.group)
    te.solve(partition_tm)

# with open('../test/data/connection.json') as f:
#       connection= json.load(f)
#
# g = GetNetworkToplogy(25,0.4)
# print(Heuristic_CSP(connection,g))



