"""
Solver tests that use some static topology files.  These tests used to
be in sdx-controller.
"""
import json
import unittest

from sdx.pce.load_balancing.te_solver import TESolver
from sdx.pce.models import ConnectionSolution
from sdx.pce.topology.temanager import TEManager

from . import TestData


class TESolverTests(unittest.TestCase):
    """
    Check that the solver from pce does what we expects it to do.
    """

    TOPOLOGY_FILE_LIST = [
        TestData.TOPOLOGY_FILE_AMLIGHT,
        TestData.TOPOLOGY_FILE_ZAOXI,
        TestData.TOPOLOGY_FILE_SAX,
    ]
    TOPOLOGY_FILE_LIST_UPDATE = [
        TestData.TOPOLOGY_FILE_AMLIGHT,
        TestData.TOPOLOGY_FILE_ZAOXI,
        TestData.TOPOLOGY_FILE_SAX,
    ]

    def setUp(self):
        with open(TestData.TOPOLOGY_FILE_SDX, "r", encoding="utf-8") as t:
            topology_data = json.load(t)
        with open(TestData.CONNECTION_REQ, "r", encoding="utf-8") as c:
            connection_data = json.load(c)

        self.temanager = TEManager(topology_data, connection_data)

    def test_computation_breakdown(self):
        graph = self.temanager.generate_graph_te()
        connection_request = self.temanager.generate_connection_te()

        print(f"Number of nodes: {graph.number_of_nodes()}")
        print(f"Graph edges: {graph.edges}")
        print(f"Traffic Matrix: {connection_request}")

        solution = TESolver(graph, connection_request).solve()
        print(f"TESolver result: {solution}")

        self.assertIsInstance(solution, ConnectionSolution)
        self.assertEqual(solution.cost, 5.0)

        breakdown = self.temanager.generate_connection_breakdown(solution)
        print(f"Breakdown: {breakdown}")
        self.assertIsNotNone(breakdown)

    def test_computation_breakdown_many_topologies(self):
        for topology_file in self.TOPOLOGY_FILE_LIST:
            print(f"Adding Topology: {topology_file}")
            with open(topology_file, "r", encoding="utf-8") as data_file:
                data = json.load(data_file)
                self.temanager.topology_manager.add_topology(data)

        graph = self.temanager.generate_graph_te()
        print(f"Graph: {graph}")

        connection_request = self.temanager.generate_connection_te()
        print(f"Connection Request: {connection_request}")

        conn = self.temanager.requests_connectivity(connection_request)
        print(f"Graph connectivity: {conn}")

        solution = TESolver(graph, connection_request).solve()
        print(f"TESolver result: {solution}")

        self.assertIsNotNone(solution.connection_map)
        self.assertEqual(solution.cost, 5.0)

        breakdown = self.temanager.generate_connection_breakdown(solution)
        print(f"Breakdown: {breakdown}")
        self.assertIsNotNone(breakdown)

    def test_computation_update(self):
        for topology_file in self.TOPOLOGY_FILE_LIST:
            print(f"Adding Topology: {topology_file}")
            with open(topology_file, "r", encoding="utf-8") as data_file:
                data = json.load(data_file)
                self.temanager.add_topology(data)

        for topology_file in self.TOPOLOGY_FILE_LIST_UPDATE:
            print(f"Updating Topology: {topology_file}")
            with open(topology_file, "r", encoding="utf-8") as data_file:
                data = json.load(data_file)
                self.temanager.update_topology(data)

        graph = self.temanager.generate_graph_te()
        connection_request = self.temanager.generate_connection_te()

        conn = self.temanager.requests_connectivity(connection_request)
        print(f"Graph connectivity: {conn}")

        solution = TESolver(graph, connection_request).solve()
        print(f"TESolver result: {solution}")

        self.assertIsNotNone(solution.connection_map)
        self.assertEqual(solution.cost, 5.0)

        breakdown = self.temanager.generate_connection_breakdown(solution)
        print(f"Breakdown: {breakdown}")
        self.assertIsNotNone(breakdown)


if __name__ == "__main__":
    unittest.main()
