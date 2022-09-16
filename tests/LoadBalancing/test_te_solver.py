import unittest
import json

from Utility.randomTopologyGenerator import RandomtopologyGenerator
from LoadBalancing.TE_Solver import TE_Solver
import Utility.global_name as global_name

Connection = './tests/data/test_connection.json'
Solution = './tests/data/test_MC_solution.json'

class Test_TE_Solver(unittest.TestCase):
    def setUp(self):
        with open(Solution, 'r') as s:
            solution = json.load(s)    
        self.solution = solution

        graph = RandomtopologyGenerator(25, 0.4, l_bw= 2000, u_bw=3000, l_lat =1, u_lat=10, seed=2022)
        self.topology = graph.generate_graph()

        with open(Connection) as f:
            self.connection = json.load(f)

    def test_mc_solve(self):
        solver = TE_Solver()

        solver.create_data_model()

        path,result = solver.solve()

        self.assertEqual(self.solution, path)

    def test_lb_solve(self):
        solver = TE_Solver(obj = global_name.Obj_LB)

        solver.create_data_model()

        path,result = solver.solve()

        self.assertEqual(self.solution, path)   


if __name__ == '__main__':
    unittest.main()