import json
import pprint
import unittest

import networkx as nx

from sdx_pce.load_balancing.te_solver import TESolver
from sdx_pce.models import ConnectionRequest, ConnectionSolution, TrafficMatrix
from sdx_pce.topology.temanager import TEManager
from sdx_pce.utils.exceptions import TEError, UnknownRequestError, ValidationError

from . import TestData


class TEManagerTests(unittest.TestCase):
    """
    Tests for topology related functions.
    """

    def test_expand_label_range(self):
        """
        Test the _expand_label_range() method.
        """
        temanager = TEManager(
            topology_data=json.loads(TestData.TOPOLOGY_FILE_AMLIGHT.read_text())
        )

        # Test case 1: Single label range
        label_range = [[100, 105], 110]
        expanded_range = temanager._expand_label_range(label_range)
        expected_range = [100, 101, 102, 103, 104, 105, 110]
        self.assertEqual(expanded_range, expected_range)

        # Test case 2: Multiple label ranges
        label_ranges = [[200, 205], 309, "310-312"]
        expanded_ranges = temanager._expand_label_range(label_ranges)
        expected_ranges = [
            200,
            201,
            202,
            203,
            204,
            205,
            309,
            310,
            311,
            312,
        ]
        self.assertEqual(expanded_ranges, expected_ranges)

        # Test case 3: Empty label range
        label_range = []
        expanded_range = temanager._expand_label_range(label_range)
        expected_range = []
        self.assertEqual(expanded_range, expected_range)

    def test_find_common_vlan_on_link(self):
        """
        Test the _find_common_vlan_on_link() method.
        """
        # Load topologies
        sax_topology = json.loads(TestData.TOPOLOGY_FILE_SAX.read_text())
        zaoxi_topology = json.loads(TestData.TOPOLOGY_FILE_ZAOXI.read_text())

        # Initialize TEManager and add topologies
        temanager = TEManager(topology_data=None)
        temanager.add_topology(sax_topology)
        temanager._update_vlan_tags_table(
            domain_name=sax_topology.get("id"),
            port_map=temanager.topology_manager.get_port_map(),
        )

        temanager.add_topology(zaoxi_topology)
        temanager._update_vlan_tags_table(
            domain_name=zaoxi_topology.get("id"),
            port_map=temanager.topology_manager.get_port_map(),
        )

        # Define test cases
        test_cases = [
            {
                "domain": "urn:sdx:topology:sax.net",
                "upstream_egress": "urn:sdx:port:sax:B3:1",
                "next_domain": "urn:sdx:topology:zaoxi.net",
                "downstream_ingress": "urn:sdx:port:zaoxi:B1:1",
                "expected_vlan": 100,  # Example expected VLAN
            },
            #
            # {
            #    "domain": "urn:sdx:topology:sax.net",
            #    "upstream_egress": "urn:sdx:port:sax.net:SAX2:1",
            #    "next_domain": "urn:sdx:topology:zaoxi.net",
            #    "downstream_ingress": "urn:sdx:port:zaoxi.net:ZAOXI2:1",
            #    "expected_vlan": None,  # Example expected VLAN when no common VLAN exists
            # },
        ]

        for case in test_cases:
            with self.subTest(case=case):
                common_vlan = temanager._find_common_vlan_on_link(
                    case["domain"],
                    case["upstream_egress"],
                    case["next_domain"],
                    case["downstream_ingress"],
                )
                self.assertEqual(common_vlan, case["expected_vlan"])

    def test_generate_solver_input(self):
        print("Test Convert Connection To Topology")
        request = json.loads(TestData.CONNECTION_REQ_AMLIGHT.read_text())

        temanager = TEManager(
            topology_data=json.loads(TestData.TOPOLOGY_FILE_AMLIGHT.read_text())
        )

        connection = self._make_traffic_matrix_from_request(temanager, request)
        self.assertIsNotNone(connection)

    def test_connection_breakdown_none_input(self):
        # Expect no breakdown when input is None.
        """
        Test that generate_connection_breakdown() raises an exception
        when given invalid input.
        """
        invalid_solution = None
        invalid_request = None

        with self.assertRaises(TEError):
            temanager = TEManager(topology_data=None)
            temanager.generate_connection_breakdown(invalid_solution, invalid_request)

    def test_connection_breakdown_tm(self):
        # Breaking down a traffic matrix.
        request = [
            {
                "1": [[0, 1], [1, 2]],
            },
            1.0,
        ]

        temanager = TEManager(
            topology_data=json.loads(TestData.TOPOLOGY_FILE_AMLIGHT.read_text())
        )

        solution = self._make_tm_and_solve(temanager, request)

        # We must have found a solution.
        self.assertIsNotNone(solution.connection_map)
        self.assertNotEqual(solution.cost, 0)

        breakdown = temanager.generate_connection_breakdown(solution, request)
        print(f"Breakdown: {breakdown}")
        self.assertIsNotNone(breakdown)
        self.assertIsInstance(breakdown, dict)
        self.assertEqual(len(breakdown), 1)

        # Make sure that breakdown contains domains as keys, and dicts
        # as values.  The domain name is a little goofy, because the
        # topology we have is goofy.
        link = breakdown.get("urn:sdx:topology:amlight.net")
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

        temanager = TEManager(
            topology_data=json.loads(TestData.TOPOLOGY_FILE_AMLIGHT.read_text())
        )

        solution = self._make_tm_and_solve(temanager, request)
        self.assertIsNotNone(solution.connection_map)
        self.assertNotEqual(solution.cost, 0)

        breakdown = temanager.generate_connection_breakdown(solution, request)
        print(f"Breakdown: {breakdown}")

        self.assertIsNotNone(breakdown)
        self.assertIsInstance(breakdown, dict)
        self.assertEqual(len(breakdown), 1)

        link = breakdown.get("urn:sdx:topology:amlight.net")
        self.assertIsInstance(link, dict)

    def test_connection_breakdown_three_domains(self):
        # SDX already exists in the known topology from setUp
        # step. Add SAX topology.
        temanager = TEManager(topology_data=None)

        for topology_file in [
            TestData.TOPOLOGY_FILE_AMLIGHT,
            TestData.TOPOLOGY_FILE_SAX,
            TestData.TOPOLOGY_FILE_ZAOXI,
        ]:
            temanager.add_topology(json.loads(topology_file.read_text()))

        topology_map = temanager.get_topology_map()
        self.assertIsInstance(topology_map, dict)

        for num, val in enumerate(topology_map.values()):
            print(f"TE topology #{num}: {val}")

        request = [
            {
                "1": [[1, 2], [3, 4]],
                "2": [[1, 2], [3, 5]],
                "3": [[7, 8], [8, 9]],
            },
            1.0,
        ]

        solution = self._make_tm_and_solve(temanager, request)
        self.assertIsNotNone(solution.connection_map)
        self.assertNotEqual(solution.cost, 0)

        breakdown = temanager.generate_connection_breakdown(solution, request)
        print(f"Breakdown: {breakdown}")

        self.assertIsNotNone(breakdown)
        self.assertIsInstance(breakdown, dict)
        self.assertEqual(len(breakdown), 3)

        amlight = breakdown.get("urn:sdx:topology:amlight.net")
        zaoxi = breakdown.get("urn:sdx:topology:zaoxi.net")
        sax = breakdown.get("urn:sdx:topology:sax.net")

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
        temanager = TEManager(topology_data=None)

        for topology_file in [
            TestData.TOPOLOGY_FILE_AMLIGHT,
            TestData.TOPOLOGY_FILE_SAX,
            TestData.TOPOLOGY_FILE_ZAOXI,
        ]:
            temanager.add_topology(json.loads(topology_file.read_text()))

        request = [
            {
                "1": [[6, 9]],
            },
            1.0,
        ]

        solution = self._make_tm_and_solve(temanager, request)

        print(f"topology: {temanager.topology_manager.get_topology()}")
        # print(f"topology_list: {temanager.topology_manager._topology_map}")

        self.assertIsNotNone(solution.connection_map)
        self.assertNotEqual(solution.cost, 0)

        breakdown = temanager.generate_connection_breakdown(solution, request)
        print(f"Breakdown: {breakdown}")

        sax = breakdown.get("urn:sdx:topology:sax.net")
        print(f"Breakdown, SAX: {sax}")

        zaoxi = breakdown.get("urn:sdx:topology:zaoxi.net")
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

        temanager = TEManager(
            topology_data=json.loads(TestData.TOPOLOGY_FILE_AMLIGHT.read_text())
        )

        solution = self._make_tm_and_solve(temanager, request)
        self.assertIsNone(solution.connection_map)
        self.assertEqual(solution.cost, 0)

        # If there's no solution, there should be no breakdown either.
        with self.assertRaises(TEError):
            temanager.generate_connection_breakdown(solution, request)

    def test_generate_graph_and_connection_with_sax_2_invalid(self):
        """
        This is a test added to investigate
        https://github.com/atlanticwave-sdx/pce/issues/107

        TODO: Use a better name for this method.
        """
        temanager = TEManager(
            topology_data=json.loads(TestData.TOPOLOGY_FILE_SAX_2.read_text())
        )

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
        temanager = TEManager(
            topology_data=json.loads(TestData.TOPOLOGY_FILE_SAX_2.read_text())
        )

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
            self.assertEqual(request.required_latency, float("inf"))

        solver = TESolver(graph, tm)
        self.assertIsNotNone(solver)

        # Solver will find a solution here.
        solution = solver.solve()
        print(f"Solution to tm {tm}: {solution}")
        self.assertIsNotNone(solution.connection_map, None)
        self.assertEqual(solution.cost, 1.0)

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

    def test_connection_amlight_v2(self):
        """
        Test with just one topology/domain.
        """
        topology = json.loads(TestData.TOPOLOGY_FILE_AMLIGHT_v2.read_text())
        temanager = TEManager(topology_data=topology)
        graph = temanager.generate_graph_te()

        self.assertIsInstance(graph, nx.Graph)

        request = {
            "name": "new-connection",
            "id": "123",
            "endpoints": [
                {"port_id": "urn:sdx:port:ampath.net:Ampath1:50", "vlan": "777"},
                {"port_id": "urn:sdx:port:ampath.net:Ampath2:50", "vlan": "777"},
            ],
            "qos_metrics": {},
            "scheduling": {},
        }

        traffic_matrix = temanager.generate_traffic_matrix(request)
        self.assertIsInstance(traffic_matrix, TrafficMatrix)

        solution = TESolver(graph, traffic_matrix).solve()
        self.assertIsInstance(solution, ConnectionSolution)
        # all links are up and enable, so path length should be 1
        self.assertEqual(len(next(iter(solution.connection_map.values()))), 1)

        topology["links"][2]["state"] = "disabled"
        temanager.update_topology(topology)

        graph = temanager.generate_graph_te()
        solution = TESolver(graph, traffic_matrix).solve()
        self.assertIsInstance(solution, ConnectionSolution)
        # now direct link is disabled, path size should be 2:
        #   (ampath1, ampath3), (ampath3, ampath2)
        self.assertEqual(len(next(iter(solution.connection_map.values()))), 2)

    def test_connection_amlight_user_port(self):
        """
        Test with just one topology/domain.
        """
        temanager = TEManager(topology_data=None)

        topology = json.loads(TestData.TOPOLOGY_FILE_AMLIGHT_USER_PORT.read_text())
        temanager.add_topology(topology)
        graph = temanager.generate_graph_te()

        self.assertIsInstance(graph, nx.Graph)

        connection_request = json.loads(
            TestData.CONNECTION_REQ_AMLIGHT_USER_PORT.read_text()
        )
        print(f"connection request: {connection_request}")

        traffic_matrix = temanager.generate_traffic_matrix(connection_request)
        self.assertIsInstance(traffic_matrix, TrafficMatrix)

        solution = TESolver(graph, traffic_matrix).solve()
        print(f"TESolver result: {solution}")
        self.assertIsInstance(solution, ConnectionSolution)

        _, links = temanager.get_links_on_path(solution)
        print(f"Links on path: {links}")

        # Make a flat list of links in connection solution dict, and
        # check that we have the same number of links.
        values = sum([v for v in solution.connection_map.values()], [])
        self.assertEqual(len(links), len(values))

        breakdown = temanager.generate_connection_breakdown(
            solution, connection_request
        )
        print(f"breakdown: {json.dumps(breakdown)}")

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

        _, links = temanager.get_links_on_path(solution)
        print(f"Links on path: {links}")

        # Make a flat list of links in connection solution dict, and
        # check that we have the same number of links.
        values = sum([v for v in solution.connection_map.values()], [])
        self.assertEqual(len(links), len(values))

        breakdown = temanager.generate_connection_breakdown(
            solution, connection_request
        )
        print(f"breakdown: {json.dumps(breakdown)}")

        connection_request = temanager.add_breakdowns_to_connection(
            connection_request, breakdown
        )

        temanager._logger.info(
            f"connection_request with breakdowns: {connection_request}"
        )

        # Note that the "domain" key is correct in the breakdown
        # result when we initialize TEManager with None for topology,
        # and later add individual topologies with add_topology().
        zaoxi = breakdown.get("urn:sdx:topology:zaoxi.net")
        sax = breakdown.get("urn:sdx:topology:sax.net")
        amlight = breakdown.get("urn:sdx:topology:amlight.net")

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

    def test_connection_amlight_to_zaoxi_user_port(self):
        """
        Exercise a connection request between Amlight and Zaoxi.
        """
        temanager = TEManager(topology_data=None)

        for path in (
            TestData.TOPOLOGY_FILE_AMLIGHT_USER_PORT,
            TestData.TOPOLOGY_FILE_SAX,
            TestData.TOPOLOGY_FILE_ZAOXI,
        ):
            topology = json.loads(path.read_text())
            temanager.add_topology(topology)

        graph = temanager.generate_graph_te()

        connection_request = json.loads(
            TestData.CONNECTION_REQ_AMLIGHT_ZAOXI_USER_PORT.read_text()
        )
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

        _, links = temanager.get_links_on_path(solution)
        print(f"Links on path: {links}")

        # Make a flat list of links in connection solution dict, and
        # check that we have the same number of links.
        values = sum([v for v in solution.connection_map.values()], [])
        self.assertEqual(len(links), len(values))

        breakdown = temanager.generate_connection_breakdown(
            solution, connection_request
        )
        print(f"breakdown: {json.dumps(breakdown)}")

        # Note that the "domain" key is correct in the breakdown
        # result when we initialize TEManager with None for topology,
        # and later add individual topologies with add_topology().
        zaoxi = breakdown.get("urn:sdx:topology:zaoxi.net")
        sax = breakdown.get("urn:sdx:topology:sax.net")
        amlight = breakdown.get("urn:sdx:topology:amlight.net")

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

    def test_delete_connection(self):
        """
        Test the deletion of a connection.
        """
        temanager = TEManager(topology_data=None)

        # Add topologies
        for path in (
            TestData.TOPOLOGY_FILE_AMLIGHT_v2,
            TestData.TOPOLOGY_FILE_SAX_v2,
            TestData.TOPOLOGY_FILE_ZAOXI_v2,
        ):
            topology = json.loads(path.read_text())
            temanager.add_topology(topology)

        # Generate graph
        graph = temanager.generate_graph_te()
        self.assertIsInstance(graph, nx.Graph)

        # Create a connection request
        connection_request = json.loads(
            TestData.CONNECTION_REQ_AMLIGHT_SAX_v2.read_text()
        )
        traffic_matrix = temanager.generate_traffic_matrix(connection_request)
        self.assertIsInstance(traffic_matrix, TrafficMatrix)

        # Solve the connection request
        solution = TESolver(graph, traffic_matrix).solve()
        self.assertIsNotNone(solution.connection_map)

        # Add the connection to the TEManager
        temanager.generate_connection_breakdown(solution, connection_request)

        # Verify the connection exists
        connections = temanager.get_connections()
        self.assertIn(connection_request["id"], connections)

        # Delete the connection
        temanager.delete_connection(connection_request["id"])

        # Verify the connection has been deleted
        connections = temanager.get_connections()
        self.assertNotIn(connection_request["id"], connections)

    def test_connection_amlight_to_sax_v2(self):
        """
        Exercise a connection request between Amlight and Zaoxi.
        """
        temanager = TEManager(topology_data=None)

        for path in (
            TestData.TOPOLOGY_FILE_AMLIGHT_v2,
            TestData.TOPOLOGY_FILE_SAX_v2,
            TestData.TOPOLOGY_FILE_ZAOXI_v2,
        ):
            topology = json.loads(path.read_text())
            temanager.add_topology(topology)

        graph = temanager.generate_graph_te()

        connection_request = json.loads(
            TestData.CONNECTION_REQ_AMLIGHT_SAX_v2.read_text()
        )
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

        _, links = temanager.get_links_on_path(solution)
        print(f"Links on path: {links}")

        # Make a flat list of links in connection solution dict, and
        # check that we have the same number of links.
        values = sum([v for v in solution.connection_map.values()], [])
        self.assertEqual(len(links), len(values))

        breakdown = temanager.generate_connection_breakdown(
            solution, connection_request
        )
        print(f"breakdown: {json.dumps(breakdown)}")

        # Note that the "domain" key is correct in the breakdown
        # result when we initialize TEManager with None for topology,
        # and later add individual topologies with add_topology().
        zaoxi = breakdown.get("urn:sdx:topology:zaoxi.net")
        print(f"Breakdown, ZAOXI: {zaoxi}")
        sax = breakdown.get("urn:sdx:topology:sax.net")
        print(f"Breakdown, SAX: {sax}")
        amlight = breakdown.get("urn:sdx:topology:ampath.net")
        print(f"Breakdown, AMLIGHT: {amlight}")

        for segment in [sax, amlight]:
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

        breakdown = temanager.generate_connection_breakdown(
            solution, connection_request
        )
        print(f"breakdown: {json.dumps(breakdown)}")

        graph = TESolver(graph, traffic_matrix).update_graph(graph, solution)

        zaoxi = breakdown.get("urn:sdx:topology:zaoxi.net")
        sax = breakdown.get("urn:sdx:topology:sax.net")
        amlight = breakdown.get("urn:sdx:topology:amlight.net")

        # Find solution for another identical connection request, and
        # compare solutions.  They should be different.
        traffic_matrix2 = temanager.generate_traffic_matrix(connection_request)

        solution = TESolver(graph, traffic_matrix2).solve()
        print(f"TESolver result: {solution}")

        self.assertIsNotNone(solution.connection_map)

        breakdown2 = temanager.generate_connection_breakdown(
            solution, connection_request
        )
        print(f"breakdown2: {json.dumps(breakdown2)}")

        self.assertNotEqual(breakdown, breakdown2)

        zaoxi2 = breakdown2.get("urn:sdx:topology:zaoxi.net")
        sax2 = breakdown2.get("urn:sdx:topology:sax.net")
        amlight2 = breakdown2.get("urn:sdx:topology:amlight.net")

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

        for i in range(0, num_requests):
            # Give each connection request a unique ID.
            connection_request["id"] = f"{self.id()}-#{i}"
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

            breakdown = json.dumps(
                temanager.generate_connection_breakdown(solution, connection_request)
            )

            print(f"breakdown: {breakdown}")
            self.assertIsNotNone(breakdown)

            breakdowns.add(breakdown)

            graph = TESolver(graph, traffic_matrix).update_graph(graph, solution)

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

        breakdown1 = temanager.generate_connection_breakdown(
            solution1, connection_request1
        )
        print(f"Breakdown #1: {json.dumps(breakdown1)}")
        # update the available bandwdith on the graph
        graph = TESolver(graph, traffic_matrix1).update_graph(graph, solution1)

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

        breakdown2 = temanager.generate_connection_breakdown(
            solution2, connection_request2
        )
        print(f"Breakdown #2: {json.dumps(breakdown2)}")

        self.assertNotEqual(connection_request1, connection_request2)
        self.assertNotEqual(traffic_matrix1, traffic_matrix2)
        self.assertNotEqual(solution1, solution2)
        self.assertNotEqual(breakdown1, breakdown2)

    def test_connection_amlight_to_zaoxi_two_distinct_requests_concurrent(self):
        """
        Test with two distinct connections in one request. The process includes Four steps:
        Step 1: Get the topology
        Step 2: Pack all connections in a list
        Step 3: Call the TESolver to get the solution: <connection, path>
        Step 4: Iterate over the solution to call the temanager.generate_connection_breakdown()
        to the get the breakdowns for each connection in the request
        """

        # Step 1: topology
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

        # Step 2: connections
        connection_object_map = {}
        # Use a connection request that should span all three domains.
        connection_request1 = json.loads(TestData.CONNECTION_REQ.read_text())
        print(f"Connection request #1: {connection_request1}")
        traffic_matrix = temanager.generate_traffic_matrix(connection_request1)

        print(f"Traffic matrix #1: '{traffic_matrix}'")
        self.assertIsInstance(traffic_matrix, TrafficMatrix)
        connection_object_map[traffic_matrix.connection_requests[0]] = (
            connection_request1
        )

        # Use another connection request that spans just one domain.
        connection_request2 = json.loads(TestData.CONNECTION_REQ_AMLIGHT.read_text())
        print(f"Connection request #2: {connection_request2}")

        traffic_matrix2 = temanager.generate_traffic_matrix(connection_request2)
        print(f"Traffic matrix #2: '{traffic_matrix2}'")
        self.assertIsInstance(traffic_matrix2, TrafficMatrix)

        traffic_matrix.connection_requests.append(
            traffic_matrix2.connection_requests[0]
        )
        connection_object_map[traffic_matrix2.connection_requests[0]] = (
            connection_request2
        )

        # Step 3: solve the TE for all connections
        solution = TESolver(graph, traffic_matrix).solve()
        print(f"TESolver result: {solution}")

        self.assertIsInstance(solution, ConnectionSolution)
        self.assertIsNotNone(solution.connection_map)

        # Step 4: obtain the breakdowns for each connection
        for connection_request, connection_solution in solution.connection_map.items():
            result = ConnectionSolution(
                connection_map={}, cost=None, request_id=traffic_matrix.request_id
            )
            result.connection_map[connection_request] = connection_solution
            breakdown = temanager.generate_connection_breakdown(
                result, connection_object_map[connection_request]
            )
            temanager._logger.info(
                (
                    f"For connection: {json.dumps(connection_object_map[connection_request])}"
                )
            )
            temanager._logger.info((f"Breakdown: {json.dumps(breakdown)}"))
            self.assertIsNotNone(breakdown)

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

        breakdown1 = temanager.generate_connection_breakdown(
            solution, connection_request
        )
        print(f"breakdown1: {json.dumps(breakdown1)}")

        # Return all used VLANs.
        temanager.unreserve_vlan(request_id=connection_request.get("id"))

        # Can we get the same breakdown for the same request now?
        breakdown2 = temanager.generate_connection_breakdown(
            solution, connection_request
        )
        print(f"breakdown2: {json.dumps(breakdown2)}")

        self.assertEqual(breakdown1, breakdown2)

        # If we generate another breakdown without un-reserving any
        # VLANs, the result should be distinct from the previous ones.
        breakdown3 = temanager.generate_connection_breakdown(
            solution, connection_request
        )
        print(f"breakdown3: {json.dumps(breakdown3)}")
        self.assertNotEqual(breakdown1, breakdown3)
        self.assertNotEqual(breakdown2, breakdown3)

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

        breakdown = temanager.generate_connection_breakdown(
            solution, connection_request
        )
        print(f"breakdown: {json.dumps(breakdown)}")

        # Note that the "domain" key is wrong in the results when we
        # initialize TEManager with a merged topology.
        self.assertIsNotNone(breakdown.get("urn:sdx"))

    def test_generate_graph_and_connection(self):
        temanager = TEManager(
            topology_data=json.loads(TestData.TOPOLOGY_FILE_AMLIGHT.read_text())
        )

        graph = temanager.generate_graph_te()

        print(f"graph: {graph}")
        self.assertIsNotNone(graph)
        self.assertIsInstance(graph, nx.Graph)

        request = json.loads(TestData.CONNECTION_REQ_AMLIGHT.read_text())
        tm = temanager.generate_traffic_matrix(request)

        print(f"tm: {tm}")
        self.assertIsNotNone(tm)
        self.assertIsInstance(tm, TrafficMatrix)

    def _make_traffic_matrix_from_request(
        self, temanager: TEManager, connection_request: dict
    ) -> TrafficMatrix:
        """
        Make a traffic matrix out of a connection request dict.
        """
        graph = temanager.graph
        print(f"Generated networkx graph of the topology: {graph}")
        print(f"Graph nodes: {graph.nodes[0]}, edges: {graph.edges}")

        traffic_matrix = temanager.generate_traffic_matrix(connection_request)
        print(f"traffic_matrix: {traffic_matrix}")

        return traffic_matrix

    def _make_tm_and_solve(self, temanager, request) -> ConnectionSolution:
        """
        Make a traffic matrix from plain old style requests (used in
        the test methods below), and solve it.
        """

        # Make a connection request.
        tm = self._make_traffic_matrix_from_list(request)
        print(f"tm: {tm}")

        graph = temanager.generate_graph_te()
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

    def test_connection_amlight_to_zaoxi_user_port_v2(self):
        """
        Exercise a connection request between Amlight and Zaoxi.
        """
        temanager = TEManager(topology_data=None)

        for path in (
            TestData.TOPOLOGY_FILE_AMLIGHT_USER_PORT,
            TestData.TOPOLOGY_FILE_SAX,
            TestData.TOPOLOGY_FILE_ZAOXI,
        ):
            topology = json.loads(path.read_text())
            temanager.add_topology(topology)

        graph = temanager.generate_graph_te()

        connection_request = json.loads(
            TestData.CONNECTION_REQ_AMLIGHT_ZAOXI_USER_PORT_v2.read_text()
        )

        # Modify the connection request for this test so that we have
        # a solvable one. The original one asks for (1) a VLAN that is
        # not present on the ingress port (777), and (2) a range
        # ("55:90") on the egress port.  This is an unsolvable request
        # because of (1), and an invalid one because of (2) since both
        # ports have to use a range.
        connection_request["endpoints"][0]["vlan"] = "100"
        connection_request["endpoints"][1]["vlan"] = "100"

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

        _, links = temanager.get_links_on_path(solution)
        print(f"Links on path: {links}")

        # Make a flat list of links in connection solution dict, and
        # check that we have the same number of links.
        values = sum([v for v in solution.connection_map.values()], [])
        self.assertEqual(len(links), len(values))

        breakdown = temanager.generate_connection_breakdown(
            solution, connection_request
        )
        print(f"breakdown: {json.dumps(breakdown)}")

        # Note that the "domain" key is correct in the breakdown
        # result when we initialize TEManager with None for topology,
        # and later add individual topologies with add_topology().
        zaoxi = breakdown.get("urn:sdx:topology:zaoxi.net")
        sax = breakdown.get("urn:sdx:topology:sax.net")
        amlight = breakdown.get("urn:sdx:topology:amlight.net")

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

    def test_get_failed_links(self):
        """Test get_failed_links()."""

        topology = json.loads(TestData.TOPOLOGY_FILE_AMLIGHT_v2.read_text())
        temanager = TEManager(topology)

        topology["links"][2]["status"] = "down"
        temanager.update_topology(topology)

        expected_failed_links = [
            {
                "id": "urn:sdx:link:ampath.net:Ampath1/1_Ampath2/1",
                "ports": [
                    "urn:sdx:port:ampath.net:Ampath1:1",
                    "urn:sdx:port:ampath.net:Ampath2:1",
                ],
            }
        ]

        failed_links = temanager.get_failed_links()

        self.assertEqual(failed_links, expected_failed_links)

    def test_connection_amlight_to_zaoxi_user_port_any(self):
        """
        Exercise a connection request between Amlight and Zaoxi, with
        VLAN set to "any".
        """
        temanager = TEManager(topology_data=None)

        for path in (
            TestData.TOPOLOGY_FILE_AMLIGHT_USER_PORT,
            TestData.TOPOLOGY_FILE_SAX,
            TestData.TOPOLOGY_FILE_ZAOXI,
        ):
            topology = json.loads(path.read_text())
            temanager.add_topology(topology)

        graph = temanager.generate_graph_te()

        connection_request = json.loads(
            TestData.CONNECTION_REQ_AMLIGHT_ZAOXI_USER_PORT_v2.read_text()
        )

        # Rewrite the request to have VLAN of "any".
        connection_request["endpoints"][0]["vlan"] = "untagged"
        connection_request["endpoints"][1]["vlan"] = "any"

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

        _, links = temanager.get_links_on_path(solution)
        print(f"Links on path: {links}")

        # Make a flat list of links in connection solution dict, and
        # check that we have the same number of links.
        values = sum([v for v in solution.connection_map.values()], [])
        self.assertEqual(len(links), len(values))

        breakdown = temanager.generate_connection_breakdown(
            solution, connection_request
        )
        print(f"breakdown: {json.dumps(breakdown)}")

        # Now assert that the breakdown has everything we need.
        zaoxi = breakdown.get("urn:sdx:topology:zaoxi.net")
        sax = breakdown.get("urn:sdx:topology:sax.net")
        amlight = breakdown.get("urn:sdx:topology:amlight.net")

        for segment in [zaoxi, sax, amlight]:
            self.assertIsInstance(segment, dict)
            self.assertIsInstance(segment.get("name"), str)
            self.assertIsInstance(segment.get("dynamic_backup_path"), bool)
            self.assertIsInstance(segment.get("uni_a"), dict)
            self.assertIsInstance(segment.get("uni_a").get("tag"), dict)
            # self.assertIsInstance(segment.get("uni_a").get("tag").get("value"), int)
            self.assertIsInstance(segment.get("uni_a").get("tag").get("tag_type"), int)
            self.assertIsInstance(segment.get("uni_a").get("port_id"), str)
            self.assertIsInstance(segment.get("uni_z"), dict)
            self.assertIsInstance(segment.get("uni_z").get("tag"), dict)
            self.assertIsInstance(segment.get("uni_z").get("tag").get("value"), int)
            self.assertIsInstance(segment.get("uni_z").get("tag").get("tag_type"), int)
            self.assertIsInstance(segment.get("uni_z").get("port_id"), str)

    def test_unreserve_unknown_connection_requests(self):
        """
        TEManager should raise an error if we attempt to unreserve a
        non-existent connection request.
        """
        request_id = "non-existent-request-id"

        with self.assertRaises(UnknownRequestError) as e:
            TEManager(topology_data=None).unreserve_vlan(request_id)
            self.assertEqual(e.request_id, request_id)

    def test_disallowed_vlan(self):
        """
        A test for the issue reported at
        https://github.com/atlanticwave-sdx/pce/issues/208
        """
        temanager = TEManager(topology_data=None)

        path = TestData.TOPOLOGY_FILE_AMLIGHT_USER_PORT
        topology = json.loads(path.read_text())
        temanager.add_topology(topology)

        graph = temanager.generate_graph_te()

        # Port 777 is not in the range allowed by the port.
        connection_request = json.loads(
            """
            {
                "name": "new-connection",
                "description": "a test circuit",
                "id": "test-connection-id",
                "endpoints": [
                    {
                        "port_id": "urn:sdx:port:amlight.net:A1:1",
                        "vlan": "777"
                    },
                    {
                        "port_id": "urn:sdx:port:amlight:B1:1",
                        "vlan": "55:90"
                    }
                ]
            }
            """
        )

        pprint.pprint(connection_request)

        # Keep track of the VLANs requested.
        requested_uni_a_vlan = connection_request["endpoints"][0]["vlan"]
        requested_uni_z_vlan = connection_request["endpoints"][1]["vlan"]

        print(
            f"requested_uni_a_vlan: {requested_uni_a_vlan}, "
            f"requested_uni_z_vlan: {requested_uni_z_vlan}"
        )

        traffic_matrix = temanager.generate_traffic_matrix(connection_request)

        print(f"Generated graph: '{graph}', traffic matrix: '{traffic_matrix}'")

        self.assertIsNotNone(graph)
        self.assertIsNotNone(traffic_matrix)

        conn = temanager.requests_connectivity(traffic_matrix)
        print(f"Graph connectivity: {conn}")

        solution = TESolver(graph, traffic_matrix).solve()
        print(f"TESolver result: {solution}")

        self.assertIsNotNone(solution)

        # Although we have a solution (in terms of connectivity
        # between ports), we should not have a breakdown at this
        # point, because we asked for a VLAN tag that is not present
        # on the port.
        with self.assertRaises(TEError):
            temanager.generate_connection_breakdown(solution, connection_request)

    def test_vlan_range_one_domain(self):
        """
        Test when requests are for a range like [n:m], just for one
        domain.
        """

        connection_request = {
            "name": "vlan-range-one-domain",
            "id": "id-vlan-range-one-domain",
            "endpoints": [
                {"port_id": "urn:sdx:port:ampath.net:Ampath1:50", "vlan": "100:200"},
                {"port_id": "urn:sdx:port:ampath.net:Ampath2:50", "vlan": "100:200"},
            ],
        }

        temanager = TEManager(
            topology_data=json.loads(TestData.TOPOLOGY_FILE_AMLIGHT_v2.read_text())
        )

        graph = temanager.generate_graph_te()

        traffic_matrix = temanager.generate_traffic_matrix(connection_request)

        print(f"Generated graph: '{graph}', traffic matrix: '{traffic_matrix}'")

        self.assertIsNotNone(graph)
        self.assertIsNotNone(traffic_matrix)

        conn = temanager.requests_connectivity(traffic_matrix)
        print(f"Graph connectivity: {conn}")

        solution = TESolver(graph, traffic_matrix).solve()
        print(f"TESolver result: {solution}")

        self.assertIsNotNone(solution)

        breakdown = temanager.generate_connection_breakdown(
            solution, connection_request
        )
        print(f"Breakdown: {breakdown}")

        expected_breakdown = {
            "urn:sdx:topology:ampath.net": {
                "name": "AMPATH_vlan_100:200_100:200",
                "dynamic_backup_path": True,
                "uni_a": {
                    "tag": {"value": "100:200", "tag_type": 1},
                    "port_id": "urn:sdx:port:ampath.net:Ampath1:50",
                },
                "uni_z": {
                    "tag": {"value": "100:200", "tag_type": 1},
                    "port_id": "urn:sdx:port:ampath.net:Ampath2:50",
                },
            }
        }

        self.maxDiff = None
        self.assertEqual(breakdown, expected_breakdown)

    def test_vlan_range_three_domains(self):
        """
        Test when requests are for a range like [n:m], and port
        allocations span multiple domains.
        """

        connection_request = {
            "name": "vlan-range-three-domains",
            "id": "id-vlan-range-three-domains",
            "endpoints": [
                {"port_id": "urn:sdx:port:ampath.net:Ampath1:50", "vlan": "100:200"},
                {"port_id": "urn:sdx:port:tenet.ac.za:Tenet01:50", "vlan": "100:200"},
            ],
        }

        temanager = TEManager(topology_data=None)

        for topology_file in [
            TestData.TOPOLOGY_FILE_AMLIGHT_v2,
            TestData.TOPOLOGY_FILE_ZAOXI_v2,
            TestData.TOPOLOGY_FILE_SAX_v2,
        ]:
            temanager.add_topology(json.loads(topology_file.read_text()))

        graph = temanager.generate_graph_te()
        traffic_matrix = temanager.generate_traffic_matrix(connection_request)

        print(f"Generated graph: '{graph}', traffic matrix: '{traffic_matrix}'")

        self.assertIsNotNone(graph)
        self.assertIsNotNone(traffic_matrix)

        conn = temanager.requests_connectivity(traffic_matrix)
        print(f"Graph connectivity: {conn}")

        solution = TESolver(graph, traffic_matrix).solve()
        print(f"TESolver result: {solution}")

        self.assertIsNotNone(solution)

        breakdown = temanager.generate_connection_breakdown(
            solution, connection_request
        )
        print(f"{breakdown}")

        expected_breakdown = {
            "urn:sdx:topology:ampath.net": {
                "name": "AMPATH_vlan_100:200_100:200",
                "dynamic_backup_path": True,
                "uni_a": {
                    "tag": {"value": "100:200", "tag_type": 1},
                    "port_id": "urn:sdx:port:ampath.net:Ampath1:50",
                },
                "uni_z": {
                    "tag": {"value": "100:200", "tag_type": 1},
                    "port_id": "urn:sdx:port:ampath.net:Ampath1:40",
                },
            },
            "urn:sdx:topology:sax.net": {
                "name": "SAX_vlan_100:200_100:200",
                "dynamic_backup_path": True,
                "uni_a": {
                    "tag": {"value": "100:200", "tag_type": 1},
                    "port_id": "urn:sdx:port:sax.net:Sax01:40",
                },
                "uni_z": {
                    "tag": {"value": "100:200", "tag_type": 1},
                    "port_id": "urn:sdx:port:sax.net:Sax01:41",
                },
            },
            "urn:sdx:topology:tenet.ac.za": {
                "name": "TENET_vlan_100:200_100:200",
                "dynamic_backup_path": True,
                "uni_a": {
                    "tag": {"value": "100:200", "tag_type": 1},
                    "port_id": "urn:sdx:port:tenet.ac.za:Tenet01:41",
                },
                "uni_z": {
                    "tag": {"value": "100:200", "tag_type": 1},
                    "port_id": "urn:sdx:port:tenet.ac.za:Tenet01:50",
                },
            },
        }

        self.maxDiff = None
        self.assertEqual(breakdown, expected_breakdown)

    def test_vlan_range_three_domains_anomaly(self):
        """
        Test when requests are for a range like [n:m], and port
        allocations span multiple domains.

        The anomaly is that we're not getting the port we requested on
        egress.  This test is added so that we can investigate why
        that happens.
        """

        connection_request = {
            "name": "vlan-range-three-domains",
            "id": "id-vlan-range-three-domains",
            "endpoints": [
                {"port_id": "urn:sdx:port:ampath.net:Ampath1:50", "vlan": "100:200"},
                {"port_id": "urn:sdx:port:tenet.ac.za:Tenet01:1", "vlan": "100:200"},
            ],
        }

        temanager = TEManager(topology_data=None)

        for topology_file in [
            TestData.TOPOLOGY_FILE_AMLIGHT_v2,
            TestData.TOPOLOGY_FILE_ZAOXI_v2,
            TestData.TOPOLOGY_FILE_SAX_v2,
        ]:
            temanager.add_topology(json.loads(topology_file.read_text()))

        graph = temanager.generate_graph_te()
        traffic_matrix = temanager.generate_traffic_matrix(connection_request)

        print(f"Generated graph: '{graph}', traffic matrix: '{traffic_matrix}'")

        self.assertIsNotNone(graph)
        self.assertIsNotNone(traffic_matrix)

        conn = temanager.requests_connectivity(traffic_matrix)
        print(f"Graph connectivity: {conn}")

        solution = TESolver(graph, traffic_matrix).solve()
        print(f"TESolver result: {solution}")

        self.assertIsNotNone(solution)

        breakdown = temanager.generate_connection_breakdown(
            solution, connection_request
        )
        print(f"{breakdown}")

        expected_breakdown = {
            "urn:sdx:topology:ampath.net": {
                "name": "AMPATH_vlan_100:200_100:200",
                "dynamic_backup_path": True,
                "uni_a": {
                    "tag": {"value": "100:200", "tag_type": 1},
                    "port_id": "urn:sdx:port:ampath.net:Ampath1:50",
                },
                "uni_z": {
                    "tag": {"value": "100:200", "tag_type": 1},
                    "port_id": "urn:sdx:port:ampath.net:Ampath1:40",
                },
            },
            "urn:sdx:topology:sax.net": {
                "name": "SAX_vlan_100:200_100:200",
                "dynamic_backup_path": True,
                "uni_a": {
                    "tag": {"value": "100:200", "tag_type": 1},
                    "port_id": "urn:sdx:port:sax.net:Sax01:40",
                },
                "uni_z": {
                    "tag": {"value": "100:200", "tag_type": 1},
                    "port_id": "urn:sdx:port:sax.net:Sax01:41",
                },
            },
            "urn:sdx:topology:tenet.ac.za": {
                "name": "TENET_vlan_100:200_100:200",
                "dynamic_backup_path": True,
                "uni_a": {
                    "tag": {"value": "100:200", "tag_type": 1},
                    "port_id": "urn:sdx:port:tenet.ac.za:Tenet01:41",
                },
                "uni_z": {
                    "tag": {"value": "100:200", "tag_type": 1},
                    "port_id": "urn:sdx:port:tenet.ac.za:Tenet01:50",
                },
            },
        }

        # Use the variable, just to silence the linter.
        self.assertIsInstance(expected_breakdown, dict)

        # # TODO: disabling this check for now. Will follow-up later.
        # self.maxDiff = None
        # self.assertEqual(breakdown, expected_breakdown)

    def _vlan_meets_request(self, requested_vlan: str, assigned_vlan: int) -> bool:
        """
        A helper to compare requested VLAN against the VLAN assignment
        made by PCE.
        """

        if assigned_vlan < 1 or assigned_vlan > 4095:
            raise ValueError(f"Invalid assigned_vlan: {assigned_vlan}")

        if requested_vlan == "any":
            return True

        # TODO: these have not been implemented yet.
        if requested_vlan in ["untagged", "all"]:
            return False

        try:
            # Here we count on the fact that attempting integer
            # conversion of a non-number should raise an error.
            if int(requested_vlan) == assigned_vlan:
                return True
            else:
                return False
        except ValueError:
            requested_range = [int(n) for n in requested_vlan.split(":")]
            return requested_vlan in requested_range

        raise Exception("invalid state!")

    def test_vlan_tags_table(self):
        """
        Test saving/restoring VLAN tags table.
        """
        temanager = TEManager(topology_data=None)

        for topology_file in [
            TestData.TOPOLOGY_FILE_AMLIGHT_v2,
            TestData.TOPOLOGY_FILE_ZAOXI_v2,
            TestData.TOPOLOGY_FILE_SAX_v2,
        ]:
            temanager.add_topology(json.loads(topology_file.read_text()))

        # Test getter.
        table1 = temanager.vlan_tags_table
        self.assertIsInstance(table1, dict)

        # Test setter
        temanager.vlan_tags_table = table1
        table2 = temanager.vlan_tags_table
        self.assertIsInstance(table2, dict)
        self.assertEqual(table1, table2)

    def test_vlan_tags_table_error_checks(self):
        """
        Test error checks when restoring VLAN tags table.
        """
        temanager = TEManager(topology_data=None)

        for topology_file in [
            TestData.TOPOLOGY_FILE_AMLIGHT_v2,
            TestData.TOPOLOGY_FILE_ZAOXI_v2,
            TestData.TOPOLOGY_FILE_SAX_v2,
        ]:
            temanager.add_topology(json.loads(topology_file.read_text()))

        # input must be a dict.
        with self.assertRaises(ValidationError) as ctx:
            temanager.vlan_tags_table = list()
            self.assertTrue("table ([]) is not a dict" in str(ctx.exception))

        # port_id keys in the input must be a string.
        with self.assertRaises(ValidationError) as ctx:
            temanager.vlan_tags_table = {"domain1": {1: {1: None}}}
            self.assertTrue("port_id (1) is not a str" in str(ctx.exception))

        # the "inner" VLAN allocation table must be a dict.
        with self.assertRaises(ValidationError) as ctx:
            temanager.vlan_tags_table = {"domain1": {"port1": (1, None)}}
            self.assertTrue("labels ((1, None)) is not a dict" in str(ctx.exception))

    def test_vlan_tags_table_ensure_no_existing_allocations(self):
        """
        Test that restoring VLAN tables works when there are no
        existing allocations.
        """
        temanager = TEManager(topology_data=None)

        for topology_file in [
            TestData.TOPOLOGY_FILE_AMLIGHT_v2,
            TestData.TOPOLOGY_FILE_ZAOXI_v2,
            TestData.TOPOLOGY_FILE_SAX_v2,
        ]:
            temanager.add_topology(json.loads(topology_file.read_text()))

        connection_request = {
            "name": "check-existing-vlan-allocations",
            "id": "id-check-existing-vlan-allocations",
            "endpoints": [
                {"port_id": "urn:sdx:port:ampath.net:Ampath1:50", "vlan": "100:200"},
                {"port_id": "urn:sdx:port:tenet.ac.za:Tenet01:1", "vlan": "100:200"},
            ],
        }

        graph = temanager.generate_graph_te()
        traffic_matrix = temanager.generate_traffic_matrix(connection_request)

        print(f"Generated graph: '{graph}', traffic matrix: '{traffic_matrix}'")
        self.assertIsNotNone(graph)
        self.assertIsNotNone(traffic_matrix)

        solution = TESolver(graph, traffic_matrix).solve()
        self.assertIsNotNone(solution)

        print(f"TESolver result: {solution}")
        breakdown = temanager.generate_connection_breakdown(
            solution, connection_request
        )

        print(f"Breakdown: {breakdown}")
        self.assertIsNotNone(breakdown)

        # The VLAN table should have some allocations now, and we
        # should not be able to change its state.
        with self.assertRaises(ValidationError) as ctx:
            temanager.vlan_tags_table = {"domain1": {"port1": {1: None}}}
            expected_error = (
                "Error: VLAN table is not empty:"
                "(domain: urn:sdx:topology:ampath.net, port: "
                "urn:sdx:port:ampath.net:Ampath1:40, vlan: 100)"
            )
            self.assertTrue(expected_error in str(ctx.exception))
