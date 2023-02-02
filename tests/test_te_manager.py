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
        with self.assertRaises(TypeError):
            self.temanager.generate_connection_breakdown(None)
