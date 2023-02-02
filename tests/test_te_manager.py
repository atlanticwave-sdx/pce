import json
import pathlib
import unittest

from sdx.pce.topology.temanager import TEManager


class TestTEManager(unittest.TestCase):
    """
    Tests for topology related functions.
    """

    TEST_DATA_DIR = pathlib.Path(__file__).parent.joinpath("data")
    TOPOLOGY_FILE = TEST_DATA_DIR.joinpath("sdx.json")
    CONNECTION_REQ_FILE = TEST_DATA_DIR.joinpath("test_request.json")

    def setUp(self):
        with open(self.TOPOLOGY_FILE, "r", encoding="utf-8") as fp:
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

    def test_generate_solver_input(self):
        print("Test Convert Connection To Topology")
        connection = self._make_connection()
        self.assertIsNotNone(connection)

    def test_connection_breakdown_none_input(self):
        # Expect an error to be raised.
        with self.assertRaises(AssertionError):
            self.temanager.generate_connection_breakdown(None)

    def test_connection_breakdown_some_input(self):
        self._make_connection()
        
        request = [
            {
                "1": [[1, 9], [9, 11]],
                "2": [[3, 1], [1, 12], [12, 0], [0, 18]],
                "3": [[2, 12], [12, 16], [16, 9], [9, 13]],
            },
            14195698.0,
        ]

        # TODO: use the the necessary setup so that a connection
        # breakdown can work correctly and without raising errors.
        with self.assertRaises(AssertionError):
            breakdown = self.temanager.generate_connection_breakdown(request)
            print(f"Breakdown: {breakdown}")
