import argparse
import json

from LoadBalancing.MC_Solver import runMC_Solver
from LoadBalancing.RandomTopologyGenerator import lbnxgraphgenerator
from LoadBalancing.RandomTopologyGenerator import GetNetworkToplogy

class TE_Group_Heur():
    """"
    Class for a connection (TE matrix) splitting based heuristic 
    1. Sequential: binpacking like heuristic: first-fit(any-fit)-decreasing, refined first fit (4 classes): Online
    2. Grouping: k-shortest-path based grouping: (k, then all other pairs sharing a same link) : 
        connection grouping: linear grouping (k largest items on); geometric grouping (interval [B/2^(r+1), B/2^2])  
    """

    def __init__(self, tm, topology):
        self.tm = tm
        self.topology = topology

    def ConnectionSplit(self,connection):
        pass


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
    
    def do_something(self):
        print("I did something")

    def main(self):
        """

        """
        self.do_something()

if __name__ == '__main__':

    parse = argparse.ArgumentParser()
    parse.add_argument('-c', dest='te_file', required=True, help='Input file for the connections or traiffc matrix, e.g. c connection.json. Required.', type=str)
    parse.add_argument('-n', dest='topology_file', required=True, help='Input file for the network topology, e.g. t topology.json. Required.', type=str)
    parse.add_argument('-o' , dest='result', default='OUTPUT.txt', help='Output file, e.g. o result.txt. If this option is not given, assume standard output.', type=str)

    parse.print_help()
    args = parse.parse_args()
    #result(args.te_file,args.node_name , args.result)

    with open(args.te_file) as json_file:
        connection = json.load(json_file)
    
    with open(args.topology_file) as json_file:
        topology = json.load(json_file)

    te = TE_Group_Heur(connection, topology)
    te.main()

# with open('../test/data/connection.json') as f:
#       connection= json.load(f)
#
# g = GetNetworkToplogy(25,0.4)
# print(Heuristic_CSP(connection,g))



