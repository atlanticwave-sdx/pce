import json
import pathlib
import pprint
import unittest

import networkx as nx

from sdx.pce.load_balancing.te_solver import TESolver
from sdx.pce.models import (
    ConnectionPath,
    ConnectionRequest,
    ConnectionSolution,
    TrafficMatrix,
)
from sdx.pce.topology.temanager import TEManager

from . import TestData


class TEManagerTests(unittest.TestCase):
    """
    Tests for topology related functions.
    """

    def setUp(self):
        with open(TestData.TOPOLOGY_FILE_AMLIGHT, "r", encoding="utf-8") as fp:
            topology_data = json.load(fp)

        with open(TestData.CONNECTION_REQ_AMLIGHT, "r", encoding="utf-8") as fp:
            connection_data = json.load(fp)

        self.temanager = TEManager(topology_data, connection_data)

    def tearDown(self):
        self.temanager = None

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
                "1": [[0, 1], [1, 2]],
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
                "1": [[0, 1], [1, 2]],
            },
            1.0,
        ]

        solution = self._make_tm_and_solve(request)

        # We must have found a solution.
        self.assertIsNotNone(solution.connection_map)
        self.assertNotEqual(solution.cost, 0)

        breakdown = self.temanager.generate_connection_breakdown(solution)
        print(f"Breakdown: {breakdown}")
        self.assertIsNotNone(breakdown)
        self.assertIsInstance(breakdown, dict)
        self.assertEqual(len(breakdown), 1)

        # Make sure that breakdown contains domains as keys, and dicts
        # as values.  The domain name is a little goofy, because the
        # topology we have is goofy.
        link = breakdown.get("urn:ogf:network:sdx:topology:amlight.net")
        self.assertIsInstance(link, dict)

    def test_connection_breakdown_two_similar_requests(self):
        # Solving and breaking down two similar connection requests.
        request = [
            {
                "1": [[0, 1], [1, 2]],
                "2": [[0, 1], [1, 2]],
            },
            1.0,
        ]

        solution = self._make_tm_and_solve(request)
        self.assertIsNotNone(solution.connection_map)
        self.assertNotEqual(solution.cost, 0)

        breakdown = self.temanager.generate_connection_breakdown(solution)
        print(f"Breakdown: {breakdown}")

        self.assertIsNotNone(breakdown)
        self.assertIsInstance(breakdown, dict)
        self.assertEqual(len(breakdown), 1)

        link = breakdown.get("urn:ogf:network:sdx:topology:amlight.net")
        self.assertIsInstance(link, dict)

    def test_connection_breakdown_three_domains(self):
        # SDX already exists in the known topology from setUp
        # step. Add SAX topology.
        with open(TestData.TOPOLOGY_FILE_SAX, "r", encoding="utf-8") as fp:
            topology_data = json.load(fp)
            self.temanager.add_topology(topology_data)

        # Add ZAOXI topology as well.
        with open(TestData.TOPOLOGY_FILE_ZAOXI, "r", encoding="utf-8") as fp:
            topology_data = json.load(fp)
            self.temanager.add_topology(topology_data)

        request = [
            {
                "1": [[1, 2], [3, 4]],
                "2": [[1, 2], [3, 5]],
                "3": [[7, 8], [8, 9]],
            },
            1.0,
        ]

        solution = self._make_tm_and_solve(request)
        self.assertIsNotNone(solution.connection_map)
        self.assertNotEqual(solution.cost, 0)

        breakdown = self.temanager.generate_connection_breakdown(solution)
        print(f"Breakdown: {breakdown}")

        self.assertIsNotNone(breakdown)
        self.assertIsInstance(breakdown, dict)
        self.assertEqual(len(breakdown), 3)

        amlight = breakdown.get("urn:ogf:network:sdx:topology:amlight.net")
        print(f"amlight: {amlight}")
        self.assertIsInstance(amlight, dict)
        self.assertIsInstance(amlight.get("ingress_port"), dict)
        self.assertIsInstance(amlight.get("egress_port"), dict)

        sax = breakdown.get("urn:ogf:network:sdx:topology:sax.net")
        print(f"sax: {sax}")
        self.assertIsInstance(sax, dict)
        self.assertIsInstance(sax.get("ingress_port"), dict)
        self.assertIsInstance(sax.get("egress_port"), dict)

        zaoxi = breakdown.get("urn:ogf:network:sdx:topology:zaoxi.net")
        print(f"zaoxi: {zaoxi}")
        self.assertIsInstance(zaoxi, dict)
        self.assertIsInstance(zaoxi.get("ingress_port"), dict)
        self.assertIsInstance(zaoxi.get("egress_port"), dict)

    def test_connection_breakdown_three_domains_sax_connection(self):
        """
        Test case added to investigate
        https://github.com/atlanticwave-sdx/sdx-controller/issues/146
        """
        with open(TestData.TOPOLOGY_FILE_SAX, "r", encoding="utf-8") as fp:
            topology_data = json.load(fp)
            self.temanager.add_topology(topology_data)

        # Add ZAOXI topology as well.
        with open(TestData.TOPOLOGY_FILE_ZAOXI, "r", encoding="utf-8") as fp:
            topology_data = json.load(fp)
            self.temanager.add_topology(topology_data)

        request = [
            {
                "1": [[6, 9]],
            },
            1.0,
        ]

        solution = self._make_tm_and_solve(request)

        print(f"topology: {self.temanager.topology_manager.topology}")
        print(f"topology_list: {self.temanager.topology_manager.topology_list}")

        self.assertIsNotNone(solution.connection_map)
        self.assertNotEqual(solution.cost, 0)

        breakdown = self.temanager.generate_connection_breakdown(solution)
        print(f"Breakdown: {breakdown}")

        sax = breakdown.get("urn:ogf:network:sdx:topology:sax.net")
        print(f"Breakdown, SAX: {sax}")

        zaoxi = breakdown.get("urn:ogf:network:sdx:topology:zaoxi.net")
        print(f"Breakdown, ZAOXI: {zaoxi}")

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
        breakdown = self.temanager.generate_connection_breakdown(solution)
        self.assertIsNone(breakdown)

    def test_generate_graph_and_connection_with_sax_2_invalid(self):
        """
        This is a test added to investigate
        https://github.com/atlanticwave-sdx/pce/issues/107

        TODO: Use a better name for this method.
        """
        with open(TestData.TOPOLOGY_FILE_SAX_2, "r", encoding="utf-8") as fp:
            topology_data = json.load(fp)

        with open(
            TestData.CONNECTION_REQ_FILE_SAX_2_INVALID, "r", encoding="utf-8"
        ) as fp:
            connection_data = json.load(fp)

        temanager = TEManager(topology_data, connection_data)
        self.assertIsNotNone(temanager)

        graph = temanager.generate_graph_te()
        self.assertIsNotNone(graph)
        self.assertIsInstance(graph, nx.Graph)

        # Expect None because the connection_data contains
        # unresolvable port IDs, which are not present in the given
        # topology.
        connection = temanager.generate_connection_te()
        self.assertIsNone(connection)

    def test_generate_graph_and_connection_with_sax_2_valid(self):
        """
        This is a test added to investigate
        https://github.com/atlanticwave-sdx/pce/issues/107

        TODO: Use a better name for this method.
        """
        with open(TestData.TOPOLOGY_FILE_SAX_2, "r", encoding="utf-8") as fp:
            topology_data = json.load(fp)

        with open(
            TestData.CONNECTION_REQ_FILE_SAX_2_VALID, "r", encoding="utf-8"
        ) as fp:
            connection_data = json.load(fp)

        temanager = TEManager(topology_data, connection_data)
        self.assertIsNotNone(temanager)

        graph = temanager.generate_graph_te()

        print(f"graph: {graph}")
        self.assertIsNotNone(graph)
        self.assertIsInstance(graph, nx.Graph)

        tm = temanager.generate_connection_te()
        print(f"traffic matrix: {tm}")
        self.assertIsInstance(tm, TrafficMatrix)

        self.assertIsInstance(tm.connection_requests, list)

        for request in tm.connection_requests:
            self.assertEqual(request.source, 1)
            self.assertEqual(request.destination, 0)
            self.assertEqual(request.required_bandwidth, 0)
            self.assertEqual(request.required_latency, 0)

        solver = TESolver(graph, tm)
        self.assertIsNotNone(solver)

        # Solver will fail to find a solution here.
        solution = solver.solve()
        print(f"Solution to tm {tm}: {solution}")
        self.assertIsNone(solution.connection_map, None)
        self.assertEqual(solution.cost, 0.0)

    def test_connection_amlight_to_zaoxi(self):
        """
        Exercise a connection request between Amlight and Zaoxi.
        """
        connection_request = json.loads(TestData.CONNECTION_REQ.read_text())
        print(f"connection_request: {connection_request}")

        temanager = TEManager(topology_data=None, connection_data=connection_request)

        for path in (
            TestData.TOPOLOGY_FILE_AMLIGHT,
            TestData.TOPOLOGY_FILE_SAX,
            TestData.TOPOLOGY_FILE_ZAOXI,
        ):
            topology = json.loads(path.read_text())
            temanager.add_topology(topology)

        graph = temanager.generate_graph_te()
        traffic_matrix = temanager.generate_connection_te()

        print(f"Generated graph: '{graph}', traffic matrix: '{traffic_matrix}'")

        self.assertIsNotNone(graph)
        self.assertIsNotNone(traffic_matrix)

        conn = temanager.requests_connectivity(traffic_matrix)
        print(f"Graph connectivity: {conn}")

        solution = TESolver(graph, traffic_matrix).solve()
        print(f"TESolver result: {solution}")

        self.assertIsNotNone(solution.connection_map)

        breakdown = temanager.generate_connection_breakdown(solution)
        print(f"breakdown: {json.dumps(breakdown)}")

        # Note that the "domain" key is correct in the breakdown
        # result when we initialize TEManager with None for topology,
        # and later add individual topologies with add_topology().
        self.assertIsNotNone(breakdown.get("urn:ogf:network:sdx:topology:zaoxi.net"))
        self.assertIsNotNone(breakdown.get("urn:ogf:network:sdx:topology:sax.net"))
        self.assertIsNotNone(breakdown.get("urn:ogf:network:sdx:topology:amlight.net"))

    def test_connection_amlight_to_zaoxi_with_merged_topology(self):
        """
        Solve with the "merged" topology of amlight, sax, and zaoxi.
        """

        connection_request = json.loads(TestData.CONNECTION_REQ.read_text())
        print(f"connection_request: {connection_request}")

        topology_data = json.loads(TestData.TOPOLOGY_FILE_SDX.read_text())
        print(f"topology_data: {topology_data}")

        temanager = TEManager(
            topology_data=topology_data, connection_data=connection_request
        )

        graph = temanager.generate_graph_te()
        traffic_matrix = temanager.generate_connection_te()

        print(f"Generated graph: '{graph}', traffic matrix: '{traffic_matrix}'")

        self.assertIsNotNone(graph)
        self.assertIsNotNone(traffic_matrix)

        conn = temanager.requests_connectivity(traffic_matrix)
        print(f"Graph connectivity: {conn}")

        solution = TESolver(graph, traffic_matrix).solve()
        print(f"TESolver result: {solution}")

        # This hopefully should find a solution.
        self.assertIsNotNone(solution.connection_map)

        breakdown = temanager.generate_connection_breakdown(solution)
        print(f"breakdown: {json.dumps(breakdown)}")

        # Note that the "domain" key is wrong in the results when we
        # initialize TEManager with a merged topology.
        self.assertIsNotNone(breakdown.get("urn:ogf:network:sdx"))

    def test_generate_graph_and_connection(self):
        graph = self.temanager.generate_graph_te()
        tm = self.temanager.generate_connection_te()

        print(f"graph: {graph}")
        print(f"tm: {tm}")

        self.assertIsNotNone(graph)
        self.assertIsInstance(graph, nx.Graph)

        self.assertIsNotNone(tm)
        self.assertIsInstance(tm, TrafficMatrix)

    def _make_connection(self):
        graph = self.temanager.graph
        print(f"Generated networkx graph of the topology: {graph}")
        print(f"Graph nodes: {graph.nodes[0]}, edges: {graph.edges}")

        connection = self.temanager.generate_connection_te()
        print(f"connection: {connection}")

        return connection

    def _make_tm_and_solve(self, request) -> ConnectionSolution:
        """
        Make a traffic matrix from plain old style requests (used in
        the test methods below), and solve it.
        """

        # Make a connection request.
        tm = self._make_traffic_matrix(request)
        print(f"tm: {tm}")

        graph = self.temanager.generate_graph_te()
        print(f"graph: {graph}")
        print(f"graph: {pprint.pformat(nx.to_dict_of_dicts(graph))}")

        # Find a connection solution.
        solver = TESolver(graph, tm)
        print(f"solver: {solver}")

        solution = solver.solve()
        print(f"solution: {solution}")

        return solution

    def _make_traffic_matrix(self, old_style_request: list) -> TrafficMatrix:
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
