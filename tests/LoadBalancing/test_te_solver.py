import unittest
import json

from Utility.randomTopologyGenerator import RandomTopologyGenerator
from Utility.randomConnectionGenerator import RandomConnectionGenerator
from LoadBalancing.TE_Solver import TE_Solver
import Utility.global_name as global_name

Connection = './tests/data/test_connection.json'
Solution = './tests/data/test_MC_solution.json'

N=10
class Test_TE_Solver(unittest.TestCase):
    def setUp(self):
        with open(Solution, 'r') as s:
            solution = json.load(s)    
        self.solution = solution
 
        self.graph_generator = RandomTopologyGenerator(N, 0.2, l_bw= 2000, u_bw=3000, l_lat =1, u_lat=10, seed=2022)
        self.graph_generator.generate_graph()

        self.tm_generator = RandomConnectionGenerator(N)
        self.tm = self.tm_generator.randomConnectionGenerator(3, 200, 1000, 30, 50, seed = 2022)

        #with open(Connection) as f:
        #    self.connection = json.load(f)

    def test_mc_solve(self):
        solver = TE_Solver(self.graph_generator, self.tm)

        solver.create_data_model()

        path,result = solver.solve()

        self.assertEqual(self.solution, path)

    def test_lb_solve(self):
        solver = TE_Solver(self.graph_generator, self.tm, obj = global_name.Obj_LB)

        solver.create_data_model()

        path,result = solver.solve()

        self.assertEqual(self.solution, path)   


if __name__ == '__main__':
    unittest.main()