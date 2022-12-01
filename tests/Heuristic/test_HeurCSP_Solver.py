import unittest
import json

from Heuristic.Heur import TE_Group_Solver
from LoadBalancing.RandomTopologyGenerator import GetConnection
from LoadBalancing.RandomTopologyGenerator import GetNetworkToplogy
from LoadBalancing.RandomTopologyGenerator import lbnxgraphgenerator

Topology = GetNetworkToplogy(25,0.4)
Connection = GetConnection('./tests/data/test_connection.json')
Solution = './tests/data/test_HeurCSP_solution.json'

class Test_HeurCSP_Solver(unittest.TestCase):
    def setUp(self):
        with open(Solution, 'r') as s:
            solution = json.load(s)
        self.connection = Connection
        self.topology = Topology
        self.solution = solution

        with open('./tests/data/connection.json', 'w') as json_file:
            json.dump(self.connection, json_file, indent=4)

    def test_Computation(self):
        lbnxgraphgenerator(25, 0.4, self.connection, self.topology)
        heur = TE_Group_Solver(self.topology, self.connection, 0, 1)
        result = heur.Heuristic_CSP(self.connection,self.topology)

        print(result)
        print("Self solution:")
        print(self.solution)
        #self.assertEqual(self.solution, result)


if __name__ == '__main__':
    unittest.main()




