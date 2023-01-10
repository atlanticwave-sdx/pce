import json
import os
import unittest

import networkx as nx

from sdx.pce.load_balancing.te_solver import TESolver
from sdx.pce.utils.constants import Constants
from sdx.pce.utils.random_connection_generator import RandomConnectionGenerator
from sdx.pce.utils.random_topology_generator import RandomTopologyGenerator
from sdx.pce.utils.graphviz import (
    can_read_dot_file,
    read_dot_file,
    read_topology_json_file,
)

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class TESolverTests(unittest.TestCase):
    def make_random_graph(self, num_nodes=25, num_connections=3):
        graph_generator = RandomTopologyGenerator(
            num_node=num_nodes,
            link_probability=0.1,
            l_bw=10000,
            u_bw=50000,
            l_lat=10,
            u_lat=20,
            seed=2022,
        )
        return graph_generator.generate_graph()

    def make_random_traffic_matrix(self, num_nodes=25, num_connections=3):
        tm_generator = RandomConnectionGenerator(num_nodes=num_nodes)
        return tm_generator.generate_connection(
            querynum=num_connections,
            l_bw=5000,
            u_bw=15000,
            l_lat=50,
            u_lat=80,
            seed=2022,
        )

    def test_mc_solve(self):
        graph = self.make_random_graph()
        tm = self.make_random_traffic_matrix()
        print(f"tm: {tm}")

        solver = TESolver(graph, tm, Constants.COST_FLAG_HOP)
        path, result = solver.solve()
        ordered_paths = solver.solution_translator(path, result)

        print(f"Path: {ordered_paths}")
        print(f"Optimal: {result}")

        self.assertEqual(6.0, result)

    def test_lb_solve(self):
        graph = self.make_random_graph()
        tm = self.make_random_traffic_matrix()
        print(f"tm: {tm}")

        solver = TESolver(
            graph, tm, Constants.COST_FLAG_HOP, Constants.OBJECTIVE_LOAD_BALANCING
        )
        path, result = solver.solve()
        ordered_paths = solver.solution_translator(path, result)

        print(f"Path: {ordered_paths}")
        print(f"Optimal: {result}")

        # self.assertEqual(self.solution, path)
        self.assertEqual(1.851, round(result, 3))

    def test_mc_solve_more_connections_than_nodes(self):
        graph = self.make_random_graph(num_nodes=10)

        # Exercised querynum > num_nodes code path.
        tm = self.make_random_traffic_matrix(num_nodes=10, num_connections=20)
        print(f"tm: {tm}")

        solver = TESolver(graph, tm, Constants.COST_FLAG_HOP)
        path, result = solver.solve()
        ordered_paths = solver.solution_translator(path, result)

        print(f"Path: {ordered_paths}")
        print(f"Optimal: {result}")

        # The above doesn't seem to find a solution, but hey, at least
        # we exercised one more code path without any crashes.
        self.assertIs(ordered_paths, None)
        self.assertEqual(result, 0.0)

    def test_mc_solve_5(self):
        edge_list_file = os.path.join(TEST_DATA_DIR, "test_five_node_topology.txt")
        traffic_matrix_file = os.path.join(TEST_DATA_DIR, "test_five_node_request.json")

        graph = nx.read_edgelist(
            edge_list_file,
            nodetype=int,
            data=(
                ("weight", float),
                ("bandwidth", float),
                ("latency", float),
            ),
        )

        with open(traffic_matrix_file) as f:
            tm = json.load(f)

        solver = TESolver(graph, tm, Constants.COST_FLAG_HOP)
        path, result = solver.solve()
        ordered_paths = solver.solution_translator(path, result)

        print(f"Path: {ordered_paths}")
        print(f"Optimal: {result}")

        self.assertEqual(7.0, result)

    @unittest.skipIf(not can_read_dot_file(), reason="Can't read dot file")
    def test_mc_solve_geant2012(self):
        topology_file = os.path.join(TEST_DATA_DIR, "Geant2012.dot")
        graph = read_dot_file(topology_file)

        self.assertNotEqual(graph, None, "Could not read dot file")

        connection_file = os.path.join(TEST_DATA_DIR, "test_connection.json")
        tm = read_topology_json_file(connection_file)

        self.assertNotEqual(tm, None, "Could not read connection file")

        solver = TESolver(graph, tm, Constants.COST_FLAG_HOP)
        path, result = solver.solve()
        ordered_paths = solver.solution_translator(path, result)

        print(f"Path: {ordered_paths}")
        print(f"Optimal: {result}")


if __name__ == "__main__":
    unittest.main()
