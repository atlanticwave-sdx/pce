import json
import pathlib
import pprint
import unittest

import networkx as nx

from sdx.pce.load_balancing.te_solver import TESolver
from sdx.pce.models import ConnectionPath, ConnectionRequest, TrafficMatrix
from sdx.pce.topology.temanager import TEManager


def make_traffic_matrix(old_style_request: list) -> TrafficMatrix:
    """
    Make a traffic matrix from the old-style list.

    The list contains a map of requests and cost.  The map contains a
    string key (TODO: what is this key?) and a list of lists as
    value, like so::

        [
            {
                "1": [[1, 2], [3, 4]],
                "2": [[1, 2], [3, 4]],
            },
            1.0,
        ]

    """
    assert isinstance(old_style_request, list)
    assert len(old_style_request) == 2

    requests_map = old_style_request[0]

    # TODO: what to do with this? Is it even a cost?
    cost = old_style_request[1]
    print(f"cost: {cost}")

    new_requests: list(ConnectionRequest) = []

    print(f"type of request: {type(requests_map)}")
    assert isinstance(requests_map, dict)

    for key, requests in requests_map.items():
        assert isinstance(key, str)
        assert isinstance(requests, list)
        assert len(requests) > 0

        print(f"key: {key}, request: {requests}")

        for request in requests:
            source = request[0]
            destination = request[1]

            if len(request) >= 3:
                required_bandwidth = request[2]
            else:
                # Use a very low default bandwith value in tests.
                required_bandwidth = 1

            if len(request) >= 4:
                required_latency = request[3]
            else:
                # Use a very high latency default latency value in tests.
                required_latency = 100

            assert len(request) == 2
            new_requests.append(
                ConnectionRequest(
                    source=source,
                    destination=destination,
                    required_bandwidth=required_bandwidth,
                    required_latency=required_latency,
                )
            )

    return TrafficMatrix(connection_requests=new_requests)


class TEManagerTests(unittest.TestCase):
    """
    Tests for topology related functions.
    """

    TEST_DATA_DIR = pathlib.Path(__file__).parent.joinpath("data")
    TOPOLOGY_FILE_SDX = TEST_DATA_DIR.joinpath("sdx.json")
    TOPOLOGY_FILE_ZAOXI = TEST_DATA_DIR.joinpath("zaoxi.json")
    TOPOLOGY_FILE_SAX = TEST_DATA_DIR.joinpath("sax.json")

    CONNECTION_REQ_FILE = TEST_DATA_DIR.joinpath("test_request.json")

    def setUp(self):
        with open(self.TOPOLOGY_FILE_SDX, "r", encoding="utf-8") as fp:
            topology_data = json.load(fp)

        with open(self.CONNECTION_REQ_FILE, "r", encoding="utf-8") as fp:
            connection_data = json.load(fp)

        self.temanager = TEManager(topology_data, connection_data)

    def _make_connection(self):
        graph = self.temanager.graph
        print(f"Generated networkx graph of the topology: {graph}")
        print(f"Graph nodes: {graph.nodes[0]}, edges: {graph.edges}")

        connection = self.temanager.generate_connection_te()
        print(f"connection: {connection}")

        return connection

    def _make_tm_and_solve(self, request):
        # Make a traffic matrix from plain old style requests (used in
        # the test methods below), and solve it.

        # Make a connection request.
        tm = make_traffic_matrix(request)
        print(f"tm: {tm}")

        print(f"graph: {self.temanager.graph}")
        print(f"graph: {pprint.pformat(nx.to_dict_of_dicts(self.temanager.graph))}")

        # Find a connection solution.
        solver = TESolver(self.temanager.graph, tm)
        print(f"solver: {solver}")

        solution = solver.solve()
        print(f"solution: {solution}")

        return solution

    def test_generate_solver_input(self):
        print("Test Convert Connection To Topology")
        connection = self._make_connection()
        self.assertIsNotNone(connection)

    def test_connection_breakdown_none_input(self):
        # Expect an error to be raised.
        with self.assertRaises(AssertionError):
            self.temanager.generate_connection_breakdown(None)

    def test_connection_breakdown_simple(self):
        # Test that the old way, which had plain old dicts and arrays
        # representing connection requests, still works.
        request = [
            {
                "1": [[1, 2], [3, 4]],
            },
            1.0,
        ]

        breakdown = self.temanager.generate_connection_breakdown(request)
        print(f"Breakdown: {breakdown}")
        self.assertIsNotNone(breakdown)

    def test_connection_breakdown_tm(self):
        # Breaking down a traffic matrix.
        request = [
            {
                "1": [[1, 2], [3, 4]],
            },
            1.0,
        ]

        solution = self._make_tm_and_solve(request)

        # We must have found a solution.
        self.assertIsNotNone(solution.connection_map)
        self.assertNotEqual(solution.cost, 0)

        breakdown = self.temanager.generate_connection_breakdown_tm(solution)
        print(f"Breakdown: {breakdown}")
        self.assertIsNotNone(breakdown)
        self.assertIsInstance(breakdown, dict)
        self.assertEqual(len(breakdown), 1)

    def test_connection_breakdown_two_similar_requests(self):
        # Solving and breaking down two similar connection requests.
        request = [
            {
                "1": [[1, 2], [3, 4]],
                "2": [[1, 2], [3, 4]],
            },
            1.0,
        ]

        solution = self._make_tm_and_solve(request)
        self.assertIsNotNone(solution.connection_map)
        self.assertNotEqual(solution.cost, 0)

        breakdown = self.temanager.generate_connection_breakdown_tm(solution)
        print(f"Breakdown: {breakdown}")

        self.assertIsNotNone(breakdown)
        self.assertIsInstance(breakdown, dict)
        self.assertEqual(len(breakdown), 1)

    def test_connection_breakdown_three_domains(self):
        # SDX already exists in the known topology from setUp
        # step. Add SAX topology.
        with open(self.TOPOLOGY_FILE_SAX, "r", encoding="utf-8") as fp:
            topology_data = json.load(fp)
            self.temanager.add_topology(topology_data)

        # Add ZAOXI topology as well.
        with open(self.TOPOLOGY_FILE_SAX, "r", encoding="utf-8") as fp:
            topology_data = json.load(fp)
            self.temanager.add_topology(topology_data)

        request = [
            {
                "1": [[1, 2], [3, 4]],
                "2": [[1, 2], [3, 5]],
            },
            1.0,
        ]

        solution = self._make_tm_and_solve(request)
        self.assertIsNotNone(solution.connection_map)
        self.assertNotEqual(solution.cost, 0)

        breakdown = self.temanager.generate_connection_breakdown_tm(solution)
        print(f"Breakdown: {breakdown}")

        self.assertIsNotNone(breakdown)
        self.assertIsInstance(breakdown, dict)
        self.assertEqual(len(breakdown), 2)

    def test_connection_breakdown_some_input(self):
        # The set of requests below should fail to find a solution,
        # because our graph at this point do not have enough nodes as
        # assumed by the request.
        request = [
            {
                "1": [[1, 9], [9, 11]],
                "2": [[3, 1], [1, 12], [12, 0], [0, 18]],
                "3": [[2, 12], [12, 16], [16, 9], [9, 13]],
            },
            14195698.0,
        ]

        solution = self._make_tm_and_solve(request)
        self.assertIsNone(solution.connection_map)
        self.assertEqual(solution.cost, 0)

        # If there's no solution, there should be no breakdown either.
        breakdown = self.temanager.generate_connection_breakdown_tm(solution)
        self.assertIsNone(breakdown)

    def test_generate_graph_and_connection(self):
        graph = self.temanager.generate_graph_te()
        tm = self.temanager.generate_connection_te()

        print(f"graph: {graph}")
        print(f"tm: {tm}")

        self.assertIsNotNone(graph)
        self.assertIsInstance(graph, nx.Graph)

        self.assertIsNotNone(tm)
        self.assertIsInstance(tm, TrafficMatrix)
