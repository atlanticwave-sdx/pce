import json
import pathlib
import unittest

import matplotlib.pyplot as plt
import networkx as nx

from sdx.datamodel.parsing.exceptions import DataModelException
from sdx.pce.topology.grenmlconverter import GrenmlConverter
from sdx.pce.topology.manager import TopologyManager


class TopologyManagerTests(unittest.TestCase):
    """
    Tests for TopologyManager.
    """

    TEST_DATA_DIR = pathlib.Path(__file__).parent.joinpath("data")

    TOPOLOGY_AMLIGHT = TEST_DATA_DIR.joinpath("amlight.json")
    TOPOLOGY_SAX = TEST_DATA_DIR.joinpath("sax.json")
    TOPOLOGY_ZAOXI = TEST_DATA_DIR.joinpath("zaoxi.json")

    TOPOLOGY_PNG = TEST_DATA_DIR.joinpath("sdx.png")
    TOPOLOGY_IN = TEST_DATA_DIR.joinpath("sdx.json")
    TOPOLOGY_OUT = TEST_DATA_DIR.joinpath("sdx-out.json")

    TOPOLOGY_FILE_LIST = [TOPOLOGY_AMLIGHT, TOPOLOGY_ZAOXI, TOPOLOGY_SAX]
    TOPOLOGY_FILE_LIST_UPDATE = [TOPOLOGY_ZAOXI]

    LINK_ID = "urn:ogf:network:sdx:link:amlight:A1-B2"
    INTER_LINK_ID = "urn:ogf:network:sdx:link:nni:Miami-Sanpaolo"

    def setUp(self):
        self.manager = TopologyManager()

    def test_merge_topology(self):
        print("Test Topology Merge!")

        for topology_file in self.TOPOLOGY_FILE_LIST:
            print(f"Adding Topology file: {topology_file}")
            with open(topology_file, "r", encoding="utf-8") as infile:
                self.manager.add_topology(json.load(infile))

        self.assertIsInstance(self.manager.topology.to_dict(), dict)

        with open(self.TOPOLOGY_OUT, "w") as outfile:
            json.dump(self.manager.topology.to_dict(), outfile, indent=4)


    def test_update_topology(self):
        print("Test Topology Update!")

        self.test_merge_topology()

        for topology_file in self.TOPOLOGY_FILE_LIST_UPDATE:
            print(f"Updating topology: {topology_file}")
            with open(topology_file, "r", encoding="utf-8") as infile:
                self.manager.update_topology(json.load(infile))

        self.assertIsInstance(self.manager.topology.to_dict(), dict)

        with open(self.TOPOLOGY_OUT, "w") as outfile:
            json.dump(self.manager.topology.to_dict(), outfile, indent=4)

        graph = self.manager.generate_graph()
        # pos = nx.spring_layout(graph, seed=225)  # Seed for reproducible layout
        nx.draw(graph, with_labels=True)
        plt.savefig(self.TOPOLOGY_PNG)

    def test_grenml_converter(self):
        print("Test Topology GRENML Converter")
        self.test_merge_topology()
        converter = GrenmlConverter(self.manager.get_topology())
        converter.read_topology()
        print(converter.get_xml_str())

    def test_generate_graph(self):
        print("Test Topology Graph")
        self.test_merge_topology()
        graph = self.manager.generate_graph()

        # pos = nx.spring_layout(graph, seed=225)  # Seed for reproducible layout
        nx.draw(graph, with_labels=True)
        plt.savefig(self.TOPOLOGY_PNG)

    def test_linkproperty_update(self):
        print("Test Topology Link Property Update!")

        self.test_merge_topology()
        self.manager.update_link_property(self.LINK_ID, "latency", 8)
        self.manager.update_link_property(self.INTER_LINK_ID, "latency", 8)

        self.assertIsInstance(self.manager.topology.to_dict(), dict)

        with open(self.TOPOLOGY_OUT, "w") as outfile:
            json.dump(self.manager.topology.to_dict(), outfile, indent=4)

    def test_link_property_update_json(self):
        print("Test Topology JSON Link Property Update!")

        with open(self.TOPOLOGY_IN, "r", encoding="utf-8") as infile:
            data = json.load(infile)
            self.manager.update_element_property_json(
                data, "links", self.LINK_ID, "latency", 20
            )

            self.assertIsInstance(data, dict)

            with open(self.TOPOLOGY_OUT, "w") as outfile:
                json.dump(data, outfile, indent=4)

if __name__ == "__main__":
    unittest.main()
