import json
import pathlib
import unittest

from sdx.pce.topology.temanager import TEManager

TEST_DATA_DIR = pathlib.Path(__file__).parent.joinpath("data")
TOPOLOGY_FILE = TEST_DATA_DIR.joinpath("sdx.json")
CONNECTION_REQ_FILE = TEST_DATA_DIR.joinpath("test_request.json")


class TestTopologyManager(unittest.TestCase):
    """
    Tests for topology related functions.
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_generate_solver_input(self):
        with open(TOPOLOGY_FILE, "r", encoding="utf-8") as fp:
            topology_data = json.load(fp)

        with open(CONNECTION_REQ_FILE, "r", encoding="utf-8") as fp:
            connection_data = json.load(fp)

        temanager = TEManager(topology_data, connection_data)

        graph = temanager.graph
        print(f"Generated networkx graph of the topology: {graph}")
        print(f"Graph nodes: {graph.nodes[0]}, edges: {graph.edges}")

        print("Test Convert Connection To Topology")
        connection = temanager.generate_connection_te()
        print(connection)
