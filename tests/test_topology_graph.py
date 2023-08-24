import unittest

import matplotlib.pyplot as plt
import networkx as nx

from sdx_pce.topology.manager import TopologyManager

from . import TestData


class TopologyGrpahTests(unittest.TestCase):
    """
    Test graph generation.
    """

    def __write_graph(self, infile, outfile):
        """
        Write graph images of a given topology file.
        """
        topology_manager = TopologyManager()
        topology_handler = topology_manager.topology_handler

        topology = topology_handler.import_topology(infile)
        topology_manager.set_topology(topology)

        graph = topology_manager.generate_graph()

        self.assertIsInstance(graph, nx.Graph)

        # Seed for reproducible layout
        # pos = nx.spring_layout(graph, seed=225)

        nx.draw(graph)
        plt.savefig(outfile)

        print(f"Graph has been written to {outfile}.")

    def test_generate_amlight(self):
        print("Writing amlight topology graph")
        self.__write_graph(
            infile=TestData.TOPOLOGY_FILE_AMLIGHT,
            outfile=TestData.TEST_OUTPUT_IMG_AMLIGHT,
        )

    def test_generate_sax(self):
        print("Writing sax topology graph")
        self.__write_graph(
            infile=TestData.TOPOLOGY_FILE_SAX, outfile=TestData.TEST_OUTPUT_IMG_SAX
        )

    def test_generate_zaoxi(self):
        print("Writing zaoxi topology graph")
        self.__write_graph(
            infile=TestData.TOPOLOGY_FILE_ZAOXI, outfile=TestData.TEST_OUTPUT_IMG_ZAOXI
        )
