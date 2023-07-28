import pathlib
import unittest

import matplotlib.pyplot as plt
import networkx as nx

from sdx.pce.topology.manager import TopologyManager

from . import TestData


class TopologyGrpahTests(unittest.TestCase):
    """
    Test graph generation.
    """

    def test_generate_graph(self):
        print("Test Topology Graph")

        topology_manager = TopologyManager()
        topology_handler = topology_manager.topology_handler

        topology = topology_handler.import_topology(TestData.TOPOLOGY_FILE_AMLIGHT)
        topology_manager.set_topology(topology)

        graph = topology_manager.generate_graph()

        self.assertIsInstance(graph, nx.Graph)

        # Seed for reproducible layout
        # pos = nx.spring_layout(graph, seed=225)

        nx.draw(graph)
        plt.savefig(TestData.TEST_OUTPUT_AMLIGHT_IMG)

        print(f"Graph has been written to {TestData.TEST_OUTPUT_AMLIGHT_IMG}.")
