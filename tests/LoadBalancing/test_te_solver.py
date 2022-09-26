import unittest
import json
import networkx as nx
from Utility.randomTopologyGenerator import RandomTopologyGenerator
from Utility.randomConnectionGenerator import RandomConnectionGenerator
from LoadBalancing.TE_Solver import TE_Solver
import Utility.global_name as global_name

Connection = './tests/data/test_connection.json'
Solution = './tests/data/test_MC_solution.json'

N=25
M=10
class Test_TE_Solver(unittest.TestCase):
    def setUp(self):
        with open(Solution, 'r') as s:
            solution = json.load(s)    
        self.solution = solution
 
        self.graph_generator = RandomTopologyGenerator(N, 0.4, l_bw= 10000, u_bw=50000, l_lat =10, u_lat=20, seed=2022)
        self.graph_generator.generate_graph()

        self.tm_generator = RandomConnectionGenerator(N)
        self.tm = self.tm_generator.randomConnectionGenerator(M, 5000, 15000, 50, 80, seed = 2022)

        #with open(Connection) as f:
        #    self.connection = json.load(f)

    def test_mc_solve(self):
        print("tm:"+str(self.tm))
        solver = TE_Solver(self.graph_generator, self.tm)

        solver.create_data_model()

        path,result = solver.solve()

        print("path:"+str(path))
        print("Optimal:"+str(result))

        self.assertEqual(self.solution, path)

    def test_lb_solve(self):
        solver = TE_Solver(self.graph_generator, self.tm, obj = global_name.Obj_LB)

        solver.create_data_model()

        path,result = solver.solve()

        print("path:"+str(path))
        print("Optimal:"+str(result))

        self.assertEqual(self.solution, path)   

    def test_mc_solve_5(self):
        g = nx.read_edgelist("./tests/data/test_five_node_topology.txt", nodetype=int, data=
            (("weight", float),("bandwidth", float),("latency", float),))
        self.graph_generator.set_graph(g)

        with open("./tests/data/test_five_node_request.json") as f:
           self.tm = json.load(f)

        solver = TE_Solver(self.graph_generator, self.tm)
        solver.create_data_model()
        path,result = solver.solve()

        print("path:"+str(path))
        print("Optimal:"+str(result))


if __name__ == '__main__':
    unittest.main()