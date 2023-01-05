import json
import unittest

import networkx as nx

import sdx.pce.Utility.global_name as global_name
from sdx.pce.load_balancing.TE_Solver import TE_Solver
from sdx.pce.Utility.randomConnectionGenerator import RandomConnectionGenerator
from sdx.pce.Utility.randomTopologyGenerator import RandomTopologyGenerator, dot_file

Connection = "./tests/data/test_connection.json"
Solution = "./tests/data/test_MC_solution.json"

topology_file = "./tests/data/Geant2012.dot"

N = 25
M = 3
COST_FLAG = 0


class Test_TE_Solver(unittest.TestCase):
    def setup(self):
        self.graph = None
        self.tm = None
        self.solution = None

    def random_graph(self):
        with open(Solution, "r") as s:
            solution = json.load(s)
        self.solution = solution

        graph_generator = RandomTopologyGenerator(
            N, 0.1, l_bw=10000, u_bw=50000, l_lat=10, u_lat=20, seed=2022
        )
        self.graph = graph_generator.generate_graph()

        tm_generator = RandomConnectionGenerator(N)
        self.tm = tm_generator.randomConnectionGenerator(
            M, 5000, 15000, 50, 80, seed=2022
        )

        # with open(Connection) as f:
        #    self.connection = json.load(f)

    def test_mc_solve(self):
        self.random_graph()
        print("tm:" + str(self.tm))
        solver = TE_Solver(self.graph, self.tm, COST_FLAG)

        solver.create_data_model()

        path, result = solver.solve()
        ordered_paths = solver.solution_translator(path, result)

        print("path:" + str(ordered_paths))
        print("Optimal:" + str(result))

        self.assertEqual(6.0, result)

    def test_lb_solve(self):
        self.random_graph()
        print("tm:" + str(self.tm))
        solver = TE_Solver(self.graph, self.tm, COST_FLAG, global_name.Obj_LB)

        solver.create_data_model()

        path, result = solver.solve()

        ordered_paths = solver.solution_translator(path, result)

        print("path:" + str(ordered_paths))
        print("Optimal:" + str(result))

        # self.assertEqual(self.solution, path)
        self.assertEqual(1.851, round(result, 3))

    def test_mc_solve_5(self):
        g = nx.read_edgelist(
            "./tests/data/test_five_node_topology.txt",
            nodetype=int,
            data=(
                ("weight", float),
                ("bandwidth", float),
                ("latency", float),
            ),
        )
        self.graph = g

        with open("./tests/data/test_five_node_request.json") as f:
            self.tm = json.load(f)

        solver = TE_Solver(self.graph, self.tm, COST_FLAG)
        solver.create_data_model()
        path, result = solver.solve()

        ordered_paths = solver.solution_translator(path, result)

        print("path:" + str(ordered_paths))
        print("Optimal:" + str(result))

        self.assertEqual(7.0, result)

    def test_mc_solve_geant2012(self):

        self.graph, self.tm = dot_file(topology_file, Connection)
        solver = TE_Solver(self.graph, self.tm, COST_FLAG)
        solver.create_data_model()
        path, result = solver.solve()

        ordered_paths = solver.solution_translator(path, result)

        print("path:" + str(ordered_paths))
        print("Optimal:" + str(result))


if __name__ == "__main__":
    unittest.main()
