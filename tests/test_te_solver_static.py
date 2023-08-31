"""
Solver tests that use some static topology files.  These tests used to
be in sdx-controller.
"""
import json
import unittest

from sdx_pce.load_balancing.te_solver import TESolver
from sdx_pce.models import ConnectionSolution
from sdx_pce.topology.temanager import TEManager

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
        topology_data = json.loads(TestData.TOPOLOGY_FILE_SDX.read_text())
        self.temanager = TEManager(topology_data)

        self.connection_request = json.loads(TestData.CONNECTION_REQ.read_text())

    def test_computation_breakdown(self):
        graph = self.temanager.generate_graph_te()
        tm = self.temanager.generate_traffic_matrix(self.connection_request)

        print(f"Number of nodes: {graph.number_of_nodes()}")
        print(f"Graph edges: {graph.edges}")
        print(f"Traffic Matrix: {tm}")

        solution = TESolver(graph, tm).solve()
        print(f"TESolver result: {solution}")

        self.assertIsInstance(solution, ConnectionSolution)
        self.assertEqual(solution.cost, 5.0)

        breakdown = self.temanager.generate_connection_breakdown(solution)
        print(f"Breakdown: {breakdown}")
        self.assertIsNotNone(breakdown)

    def test_computation_breakdown_many_topologies(self):
        for topology_file in self.TOPOLOGY_FILE_LIST:
            print(f"Adding Topology: {topology_file}")
            data = json.loads(topology_file.read_text())
            self.temanager.topology_manager.add_topology(data)

        graph = self.temanager.generate_graph_te()
        print(f"Graph: {graph}")

        tm = self.temanager.generate_traffic_matrix(self.connection_request)
        print(f"Traffic matrix: {tm}")

        conn = self.temanager.requests_connectivity(tm)
        print(f"Graph connectivity: {conn}")

        solution = TESolver(graph, tm).solve()
        print(f"TESolver result: {solution}")

        self.assertIsNotNone(solution.connection_map)
        self.assertEqual(solution.cost, 5.0)

        breakdown = self.temanager.generate_connection_breakdown(solution)
        print(f"Breakdown: {breakdown}")
        self.assertIsNotNone(breakdown)

    def test_computation_update(self):
        for topology_file in self.TOPOLOGY_FILE_LIST:
            print(f"Adding Topology: {topology_file}")
            data = json.loads(topology_file.read_text())
            self.temanager.add_topology(data)

        for topology_file in self.TOPOLOGY_FILE_LIST_UPDATE:
            print(f"Updating Topology: {topology_file}")
            data = json.loads(topology_file.read_text())
            self.temanager.update_topology(data)

        graph = self.temanager.generate_graph_te()
        tm = self.temanager.generate_traffic_matrix(self.connection_request)

        conn = self.temanager.requests_connectivity(tm)
        print(f"Graph connectivity: {conn}")

        solution = TESolver(graph, tm).solve()
        print(f"TESolver result: {solution}")

        self.assertIsNotNone(solution.connection_map)
        self.assertEqual(solution.cost, 5.0)

        breakdown = self.temanager.generate_connection_breakdown(solution)
        print(f"Breakdown: {breakdown}")
        self.assertIsNotNone(breakdown)


if __name__ == "__main__":
    unittest.main()
