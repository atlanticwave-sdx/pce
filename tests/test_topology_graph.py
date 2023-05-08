import pathlib
import unittest

import matplotlib.pyplot as plt
import networkx as nx

from sdx.pce.topology.manager import TopologyManager


class TopologyGrpahTests(unittest.TestCase):
    """
    Test graph generation.
    """

    TEST_DATA_DIR = pathlib.Path(__file__).parent.joinpath("data")
    TOPOLOGY_FILE_AMLIGHT = TEST_DATA_DIR.joinpath("amlight.json")
    TOPOLOGY_FILE_AMLIGHT_IMG = TEST_DATA_DIR.joinpath("amlight.png")

    def test_generate_graph(self):
        print("Test Topology Graph")

        topology_manager = TopologyManager()
        topology_handler = topology_manager.topology_handler

        topology = topology_handler.import_topology(self.TOPOLOGY_FILE_AMLIGHT)
        topology_manager.set_topology(topology)

        graph = topology_manager.generate_graph()

        self.assertIsInstance(graph, nx.Graph)

        # Seed for reproducible layout
        # pos = nx.spring_layout(graph, seed=225)

        nx.draw(graph)
        plt.savefig(self.TOPOLOGY_FILE_AMLIGHT_IMG)
