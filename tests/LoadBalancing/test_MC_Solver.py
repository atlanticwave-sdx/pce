import unittest
import json

from networkx.algorithms import approximation as approx

from LoadBalancing.MC_Solver import runMC_Solver
from LoadBalancing.RandomTopologyGenerator import GetNetworkToplogy
from LoadBalancing.RandomTopologyGenerator import GetConnection
from LoadBalancing.RandomTopologyGenerator import lbnxgraphgenerator

Topology = GetNetworkToplogy(25,0.4)
Connection = GetConnection('./tests/data/test_connection.json')
Solution = './tests/data/test_MC_solution.json'

class Test_MC_Solver(unittest.TestCase):
    def setUp(self):
        with open(Solution, 'r') as s:
            solution = json.load(s)
        self.connection = Connection
        self.topology = Topology
        self.solution = solution

        con=approx.node_connectivity(self.topology)
        print("Node connectivity:"+str(con))

        with open('./tests/data/connection.json', 'w') as json_file:
            json.dump(self.connection, json_file, indent=4)

    def test_Computation(self):
        lbnxgraphgenerator(25, 0.4, self.connection, self.topology)

        result = runMC_Solver()

        self.assertEqual(self.solution, result)


if __name__ == '__main__':
    unittest.main()