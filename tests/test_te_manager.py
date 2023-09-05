import json
import pprint
import unittest
import uuid

import networkx as nx

from sdx_pce.load_balancing.te_solver import TESolver
from sdx_pce.models import ConnectionRequest, ConnectionSolution, TrafficMatrix
from sdx_pce.topology.temanager import TEManager

from . import TestData


class TEManagerTests(unittest.TestCase):
    """
    Tests for topology related functions.
    """

    def setUp(self):
        topology = json.loads(TestData.TOPOLOGY_FILE_AMLIGHT.read_text())
        self.temanager = TEManager(topology)

    def tearDown(self):
        self.temanager = None

    def test_generate_solver_input(self):
        print("Test Convert Connection To Topology")
        request = json.loads(TestData.CONNECTION_REQ_AMLIGHT.read_text())
        connection = self._make_traffic_matrix_from_request(request)
        self.assertIsNotNone(connection)

    def test_connection_breakdown_none_input(self):
        # Expect no breakdown when input is None.
        self.assertIsNone(self.temanager.generate_connection_breakdown(None))

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
        sax_topology = json.loads(TestData.TOPOLOGY_FILE_SAX.read_text())
        self.temanager.add_topology(sax_topology)

        # Add ZAOXI topology as well.
        zaoxi_topology = json.loads(TestData.TOPOLOGY_FILE_ZAOXI.read_text())
        self.temanager.add_topology(zaoxi_topology)

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
        zaoxi = breakdown.get("urn:ogf:network:sdx:topology:zaoxi.net")
        sax = breakdown.get("urn:ogf:network:sdx:topology:sax.net")

        for segment in [zaoxi, sax, amlight]:
            self.assertIsInstance(segment, dict)
            self.assertIsInstance(segment.get("name"), str)
            self.assertIsInstance(segment.get("dynamic_backup_path"), bool)
            self.assertIsInstance(segment.get("uni_a"), dict)
            self.assertIsInstance(segment.get("uni_a").get("tag"), dict)
            self.assertIsInstance(segment.get("uni_a").get("tag").get("value"), int)
            self.assertIsInstance(segment.get("uni_a").get("tag").get("tag_type"), int)
            self.assertIsInstance(segment.get("uni_a").get("port_id"), str)
            self.assertIsInstance(segment.get("uni_z"), dict)
            self.assertIsInstance(segment.get("uni_z").get("tag"), dict)
            self.assertIsInstance(segment.get("uni_z").get("tag").get("value"), int)
            self.assertIsInstance(segment.get("uni_z").get("tag").get("tag_type"), int)
            self.assertIsInstance(segment.get("uni_z").get("port_id"), str)

    def test_connection_breakdown_three_domains_sax_connection(self):
        """
        Test case added to investigate
        https://github.com/atlanticwave-sdx/sdx-controller/issues/146
        """
        sax_topology = json.loads(TestData.TOPOLOGY_FILE_SAX.read_text())
        self.temanager.add_topology(sax_topology)

        # Add ZAOXI topology as well.
        zaoxi_topology = json.loads(TestData.TOPOLOGY_FILE_ZAOXI.read_text())
        self.temanager.add_topology(zaoxi_topology)

        request = [
            {
                "1": [[6, 9]],
            },
            1.0,
        ]

        solution = self._make_tm_and_solve(request)

        print(f"topology: {self.temanager.topology_manager.get_topology()}")
        # print(f"topology_list: {self.temanager.topology_manager._topology_map}")

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
        topology = json.loads(TestData.TOPOLOGY_FILE_SAX_2.read_text())
        temanager = TEManager(topology)

        self.assertIsNotNone(temanager)

        graph = temanager.generate_graph_te()
        self.assertIsNotNone(graph)
        self.assertIsInstance(graph, nx.Graph)

        # Expect None because the connection_data contains
        # unresolvable port IDs, which are not present in the given
        # topology.
        request = json.loads(TestData.CONNECTION_REQ_FILE_SAX_2_INVALID.read_text())
        tm = temanager.generate_traffic_matrix(request)
        self.assertIsNone(tm)

    def test_generate_graph_and_connection_with_sax_2_valid(self):
        """
        This is a test added to investigate
        https://github.com/atlanticwave-sdx/pce/issues/107

        TODO: Use a better name for this method.
        """
        topology = json.loads(TestData.TOPOLOGY_FILE_SAX_2.read_text())
        temanager = TEManager(topology)

        self.assertIsNotNone(temanager)

        graph = temanager.generate_graph_te()
        print(f"graph: {graph}")
        self.assertIsNotNone(graph)
        self.assertIsInstance(graph, nx.Graph)

        request = json.loads(TestData.CONNECTION_REQ_FILE_SAX_2_VALID.read_text())
        tm = temanager.generate_traffic_matrix(request)
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

    def test_connection_amlight(self):
        """
        Test with just one topology/domain.
        """
        temanager = TEManager(topology_data=None)

        topology = json.loads(TestData.TOPOLOGY_FILE_AMLIGHT.read_text())
        temanager.add_topology(topology)
        graph = temanager.generate_graph_te()

        self.assertIsInstance(graph, nx.Graph)

        request = json.loads(TestData.CONNECTION_REQ_AMLIGHT.read_text())
        print(f"connection request: {request}")

        traffic_matrix = temanager.generate_traffic_matrix(request)
        self.assertIsInstance(traffic_matrix, TrafficMatrix)

        solution = TESolver(graph, traffic_matrix).solve()
        print(f"TESolver result: {solution}")
        self.assertIsInstance(solution, ConnectionSolution)

    def test_connection_amlight_to_zaoxi(self):
        """
        Exercise a connection request between Amlight and Zaoxi.
        """
        temanager = TEManager(topology_data=None)

        for path in (
            TestData.TOPOLOGY_FILE_AMLIGHT,
            TestData.TOPOLOGY_FILE_SAX,
            TestData.TOPOLOGY_FILE_ZAOXI,
        ):
            topology = json.loads(path.read_text())
            temanager.add_topology(topology)

        graph = temanager.generate_graph_te()

        connection_request = json.loads(TestData.CONNECTION_REQ.read_text())
        print(f"connection_request: {connection_request}")
        traffic_matrix = temanager.generate_traffic_matrix(connection_request)

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
        zaoxi = breakdown.get("urn:ogf:network:sdx:topology:zaoxi.net")
        sax = breakdown.get("urn:ogf:network:sdx:topology:sax.net")
        amlight = breakdown.get("urn:ogf:network:sdx:topology:amlight.net")

        # Per https://github.com/atlanticwave-sdx/pce/issues/101, each
        # breakdown should be of the below form:
        #
        # {
        #     "name": "TENET_vlan_201_203_Ampath_Tenet",
        #     "dynamic_backup_path": true,
        #     "uni_a": {
        #         "tag": {
        #             "value": 203,
        #             "tag_type": 1
        #         },
        #         "interface_id": "cc:00:00:00:00:00:00:07:41"
        #     },
        #     "uni_z": {
        #         "tag": {
        #             "value": 201,
        #             "tag_type": 1
        #         },
        #         "interface_id": "cc:00:00:00:00:00:00:08:50"
        #     }
        # }
        for segment in [zaoxi, sax, amlight]:
            self.assertIsInstance(segment, dict)
            self.assertIsInstance(segment.get("name"), str)
            self.assertIsInstance(segment.get("dynamic_backup_path"), bool)
            self.assertIsInstance(segment.get("uni_a"), dict)
            self.assertIsInstance(segment.get("uni_a").get("tag"), dict)
            self.assertIsInstance(segment.get("uni_a").get("tag").get("value"), int)
            self.assertIsInstance(segment.get("uni_a").get("tag").get("tag_type"), int)
            self.assertIsInstance(segment.get("uni_a").get("port_id"), str)
            self.assertIsInstance(segment.get("uni_z"), dict)
            self.assertIsInstance(segment.get("uni_z").get("tag"), dict)
            self.assertIsInstance(segment.get("uni_z").get("tag").get("value"), int)
            self.assertIsInstance(segment.get("uni_z").get("tag").get("tag_type"), int)
            self.assertIsInstance(segment.get("uni_z").get("port_id"), str)

    def test_connection_amlight_to_zaoxi_two_identical_requests(self):
        """
        Exercise two identical connection requests.
        """
        temanager = TEManager(topology_data=None)

        for path in (
            TestData.TOPOLOGY_FILE_AMLIGHT,
            TestData.TOPOLOGY_FILE_SAX,
            TestData.TOPOLOGY_FILE_ZAOXI,
        ):
            topology = json.loads(path.read_text())
            temanager.add_topology(topology)

        graph = temanager.generate_graph_te()

        connection_request = json.loads(TestData.CONNECTION_REQ.read_text())
        print(f"connection_request: {connection_request}")
        traffic_matrix = temanager.generate_traffic_matrix(connection_request)

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

        zaoxi = breakdown.get("urn:ogf:network:sdx:topology:zaoxi.net")
        sax = breakdown.get("urn:ogf:network:sdx:topology:sax.net")
        amlight = breakdown.get("urn:ogf:network:sdx:topology:amlight.net")

        # Find solution for another identical connection request, and
        # compare solutions.  They should be different.
        traffic_matrix2 = temanager.generate_traffic_matrix(connection_request)

        solution = TESolver(graph, traffic_matrix2).solve()
        print(f"TESolver result: {solution}")

        self.assertIsNotNone(solution.connection_map)

        breakdown2 = temanager.generate_connection_breakdown(solution)
        print(f"breakdown2: {json.dumps(breakdown2)}")

        self.assertNotEqual(breakdown, breakdown2)

        zaoxi2 = breakdown2.get("urn:ogf:network:sdx:topology:zaoxi.net")
        sax2 = breakdown2.get("urn:ogf:network:sdx:topology:sax.net")
        amlight2 = breakdown2.get("urn:ogf:network:sdx:topology:amlight.net")

        self.assertNotEqual(zaoxi, zaoxi2)
        self.assertNotEqual(sax, sax2)
        self.assertNotEqual(amlight, amlight2)

        print(f"zaoxi: {zaoxi}, zaoxi2: {zaoxi2}")
        print(f"sax: {sax}, sax2: {sax2}")
        print(f"amlight: {amlight}, amlight2: {amlight2}")

    def test_connection_amlight_to_zaoxi_many_identical_requests(self):
        """
        Exercise many identical connection requests.
        """
        temanager = TEManager(topology_data=None)

        for path in (
            TestData.TOPOLOGY_FILE_AMLIGHT,
            TestData.TOPOLOGY_FILE_SAX,
            TestData.TOPOLOGY_FILE_ZAOXI,
        ):
            topology = json.loads(path.read_text())
            temanager.add_topology(topology)

        graph = temanager.generate_graph_te()

        connection_request = json.loads(TestData.CONNECTION_REQ.read_text())

        breakdowns = set()
        num_requests = 10

        for _ in range(0, num_requests):
            connection_request["id"] = str(uuid.uuid4())
            print(f"connection_request: {connection_request}")

            traffic_matrix = temanager.generate_traffic_matrix(connection_request)

            print(f"Generated graph: '{graph}', traffic matrix: '{traffic_matrix}'")

            self.assertIsNotNone(graph)
            self.assertIsNotNone(traffic_matrix)

            conn = temanager.requests_connectivity(traffic_matrix)
            print(f"Graph connectivity: {conn}")

            solution = TESolver(graph, traffic_matrix).solve()
            print(f"TESolver result: {solution}")

            self.assertIsNotNone(solution.connection_map)

            breakdown = json.dumps(temanager.generate_connection_breakdown(solution))

            print(f"breakdown: {breakdown}")
            self.assertIsNotNone(breakdown)

            breakdowns.add(breakdown)

        print(f"breakdowns: {breakdowns}")

        # Check that we have the same number of unique breakdowns as
        # connection requests.
        self.assertEqual(len(breakdowns), num_requests)

    def test_connection_amlight_to_zaoxi_two_distinct_requests(self):
        """
        Test with two distinct connection requests.
        """
        temanager = TEManager(topology_data=None)

        for path in (
            TestData.TOPOLOGY_FILE_AMLIGHT,
            TestData.TOPOLOGY_FILE_SAX,
            TestData.TOPOLOGY_FILE_ZAOXI,
        ):
            topology = json.loads(path.read_text())
            temanager.add_topology(topology)

        graph = temanager.generate_graph_te()
        print(f"Generated graph: '{graph}'")

        self.assertIsInstance(graph, nx.Graph)

        # Use a connection request that should span all three domains.
        connection_request1 = json.loads(TestData.CONNECTION_REQ.read_text())
        print(f"Connection request #1: {connection_request1}")
        traffic_matrix1 = temanager.generate_traffic_matrix(connection_request1)

        print(f"Traffic matrix #1: '{traffic_matrix1}'")
        self.assertIsInstance(traffic_matrix1, TrafficMatrix)

        solution1 = TESolver(graph, traffic_matrix1).solve()
        print(f"TESolver result #1: {solution1}")

        self.assertIsInstance(solution1, ConnectionSolution)
        self.assertIsNotNone(solution1.connection_map)

        breakdown1 = temanager.generate_connection_breakdown(solution1)
        print(f"Breakdown #1: {json.dumps(breakdown1)}")

        # Use another connection request that spans just one domain.
        connection_request2 = json.loads(TestData.CONNECTION_REQ_AMLIGHT.read_text())
        print(f"Connection request #2: {connection_request2}")

        traffic_matrix2 = temanager.generate_traffic_matrix(connection_request2)
        print(f"Traffic matrix #2: '{traffic_matrix2}'")
        self.assertIsInstance(traffic_matrix2, TrafficMatrix)

        solution2 = TESolver(graph, traffic_matrix2).solve()
        print(f"TESolver result #2: {solution2}")

        self.assertIsInstance(solution2, ConnectionSolution)
        self.assertIsNotNone(solution2.connection_map)

        breakdown2 = temanager.generate_connection_breakdown(solution2)
        print(f"Breakdown #2: {json.dumps(breakdown2)}")

        self.assertNotEqual(connection_request1, connection_request2)
        self.assertNotEqual(traffic_matrix1, traffic_matrix2)
        self.assertNotEqual(solution1, solution2)
        self.assertNotEqual(breakdown1, breakdown2)

    def test_connection_amlight_to_zaoxi_unreserve(self):
        """
        Exercise a connection request between Amlight and Zaoxi.
        """
        temanager = TEManager(topology_data=None)

        for path in (
            TestData.TOPOLOGY_FILE_AMLIGHT,
            TestData.TOPOLOGY_FILE_SAX,
            TestData.TOPOLOGY_FILE_ZAOXI,
        ):
            topology = json.loads(path.read_text())
            temanager.add_topology(topology)

        graph = temanager.generate_graph_te()

        connection_request = json.loads(TestData.CONNECTION_REQ.read_text())
        print(f"connection_request: {connection_request}")
        traffic_matrix = temanager.generate_traffic_matrix(connection_request)

        print(f"Generated graph: '{graph}', traffic matrix: '{traffic_matrix}'")

        self.assertIsNotNone(graph)
        self.assertIsNotNone(traffic_matrix)

        conn = temanager.requests_connectivity(traffic_matrix)
        print(f"Graph connectivity: {conn}")

        solution = TESolver(graph, traffic_matrix).solve()
        print(f"TESolver result: {solution}")

        self.assertIsNotNone(solution.connection_map)

        breakdown1 = temanager.generate_connection_breakdown(solution)
        print(f"breakdown1: {json.dumps(breakdown1)}")

        # Return all used VLANs.
        temanager.unreserve_vlan(request_id=connection_request.get("id"))

        # Can we get the same breakdown for the same request now?
        breakdown2 = temanager.generate_connection_breakdown(solution)
        print(f"breakdown2: {json.dumps(breakdown2)}")

        self.assertEqual(breakdown1, breakdown2)

    def test_connection_amlight_to_zaoxi_with_merged_topology(self):
        """
        Solve with the "merged" topology of amlight, sax, and zaoxi.

        Note that this does not work as it probably should -- when we
        have a merged topology, nodes do not resolve to correct
        domains.
        """
        topology_data = json.loads(TestData.TOPOLOGY_FILE_SDX.read_text())
        print(f"topology_data: {topology_data}")

        temanager = TEManager(topology_data=topology_data)

        graph = temanager.generate_graph_te()

        connection_request = json.loads(TestData.CONNECTION_REQ.read_text())
        print(f"connection_request: {connection_request}")
        traffic_matrix = temanager.generate_traffic_matrix(connection_request)

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

        print(f"graph: {graph}")
        self.assertIsNotNone(graph)
        self.assertIsInstance(graph, nx.Graph)

        request = json.loads(TestData.CONNECTION_REQ_AMLIGHT.read_text())
        tm = self.temanager.generate_traffic_matrix(request)

        print(f"tm: {tm}")
        self.assertIsNotNone(tm)
        self.assertIsInstance(tm, TrafficMatrix)

    def _make_traffic_matrix_from_request(
        self, connection_request: dict
    ) -> TrafficMatrix:
        """
        Make a traffic matrix out of a connection request dict.
        """
        graph = self.temanager.graph
        print(f"Generated networkx graph of the topology: {graph}")
        print(f"Graph nodes: {graph.nodes[0]}, edges: {graph.edges}")

        traffic_matrix = self.temanager.generate_traffic_matrix(connection_request)
        print(f"traffic_matrix: {traffic_matrix}")

        return traffic_matrix

    def _make_tm_and_solve(self, request) -> ConnectionSolution:
        """
        Make a traffic matrix from plain old style requests (used in
        the test methods below), and solve it.
        """

        # Make a connection request.
        tm = self._make_traffic_matrix_from_list(request)
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

    def _make_traffic_matrix_from_list(self, old_style_request: list) -> TrafficMatrix:
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

        return TrafficMatrix(connection_requests=new_requests, request_id=self.id())
