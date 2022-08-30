from LoadBalancing.MC_Solver import runMC_Solver
from LoadBalancing.RandomTopologyGenerator import lbnxgraphgenerator
from LoadBalancing.RandomTopologyGenerator import GetNetworkToplogy
import json


class TE_Group_Heur:
    """"
    Class for a connection (TE matrix) splitting based heuristic 
    1. Sequential: binpacking like heuristic: first-fit(any-fit)-decreasing, refined first fit (4 classes): Online
    2. Grouping: k-shortest-path based grouping: (k, then all other pairs sharing a same link) : 
        connection grouping: linear grouping (k largest items on); geometric grouping (interval [B/2^(r+1), B/2^2])  
    """

    def __init__(self):
        super.__init__()

    def ConnectionSplit(self,connection):
        with open('./tests/data/splittedconnection.json', 'w') as json_file:
            data = connection
            json.dump(data, json_file, indent=4)


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

    def main(self):
        """

        """
        print("I am the main")

if __name__ == '__main__':
    TE_Group_Heur.main()

# with open('../test/data/connection.json') as f:
#       connection= json.load(f)
#
# g = GetNetworkToplogy(25,0.4)
# print(Heuristic_CSP(connection,g))



