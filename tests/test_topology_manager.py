import json
import unittest

import matplotlib.pyplot as plt
import networkx as nx

from sdx_pce.topology.grenmlconverter import GrenmlConverter
from sdx_pce.topology.manager import TopologyManager

from . import TestData


class TopologyManagerTests(unittest.TestCase):
    """
    Tests for TopologyManager.
    """

    TOPOLOGY_PNG = TestData.TEST_DATA_DIR / "sdx.png"
    TOPOLOGY_IN = TestData.TEST_DATA_DIR / "sdx.json"
    TOPOLOGY_OUT = TestData.TEST_DATA_DIR / "sdx-out.json"

    TOPOLOGY_FILE_LIST = [
        TestData.TOPOLOGY_FILE_AMLIGHT,
        TestData.TOPOLOGY_FILE_ZAOXI,
        TestData.TOPOLOGY_FILE_SAX,
    ]
    TOPOLOGY_FILE_LIST_UPDATE = [TestData.TOPOLOGY_FILE_ZAOXI]

    LINK_ID = "urn:ogf:network:sdx:link:amlight:A1-B2"
    INTER_LINK_ID = "urn:ogf:network:sdx:link:nni:Miami-Sanpaolo"

    def setUp(self):
        self.topology_manager = TopologyManager()

    def tearDown(self):
        self.topology_manager = None

    def test_merge_topology(self):
        print("Test Topology Merge!")

        for topology_file in self.TOPOLOGY_FILE_LIST:
            print(f"Adding Topology file: {topology_file}")
            with open(topology_file, "r", encoding="utf-8") as infile:
                self.topology_manager.add_topology(json.load(infile))

        self.assertIsInstance(self.topology_manager.topology.to_dict(), dict)

        print(f"Writing result to {self.TOPOLOGY_OUT}")
        with open(self.TOPOLOGY_OUT, "w") as outfile:
            json.dump(self.topology_manager.topology.to_dict(), outfile, indent=4)

    def test_update_topology(self):
        print("Test Topology Update!")

        self.test_merge_topology()

        for topology_file in self.TOPOLOGY_FILE_LIST_UPDATE:
            print(f"Updating topology: {topology_file}")
            with open(topology_file, "r", encoding="utf-8") as infile:
                self.topology_manager.update_topology(json.load(infile))

        self.assertIsInstance(self.topology_manager.topology.to_dict(), dict)

        with open(self.TOPOLOGY_OUT, "w") as outfile:
            json.dump(self.topology_manager.topology.to_dict(), outfile, indent=4)

        graph = self.topology_manager.generate_graph()
        # pos = nx.spring_layout(graph, seed=225)  # Seed for reproducible layout
        nx.draw(graph, with_labels=True)
        plt.savefig(self.TOPOLOGY_PNG)

    def test_grenml_converter(self):
        print("Test Topology GRENML Converter")
        self.test_merge_topology()
        converter = GrenmlConverter(self.topology_manager.get_topology())
        converter.read_topology()
        xml = converter.get_xml_str()
        print(f"xml: {xml}")
        self.assertIsNotNone(xml)

    def test_generate_graph(self):
        print("Test Topology Graph")
        self.test_merge_topology()
        graph = self.topology_manager.generate_graph()

        # pos = nx.spring_layout(graph, seed=225)  # Seed for reproducible layout
        nx.draw(graph, with_labels=True)
        plt.savefig(self.TOPOLOGY_PNG)

    def test_linkproperty_update(self):
        print("Test Topology Link Property Update!")

        self.test_merge_topology()
        self.topology_manager.update_link_property(self.LINK_ID, "latency", 8)
        self.topology_manager.update_link_property(self.INTER_LINK_ID, "latency", 8)

        self.assertIsInstance(self.topology_manager.topology.to_dict(), dict)

        with open(self.TOPOLOGY_OUT, "w") as outfile:
            json.dump(self.topology_manager.topology.to_dict(), outfile, indent=4)

    def test_link_property_update_json(self):
        print("Test Topology JSON Link Property Update!")

        with open(self.TOPOLOGY_IN, "r", encoding="utf-8") as infile:
            data = json.load(infile)
            self.topology_manager.update_element_property_json(
                data, "links", self.LINK_ID, "latency", 20
            )

            self.assertIsInstance(data, dict)

            with open(self.TOPOLOGY_OUT, "w") as outfile:
                json.dump(data, outfile, indent=4)

    def test_get_domain_name(self):
        """
        Test that TopologyManager.get_domain_name() works as expected.
        """
        for topology_file in self.TOPOLOGY_FILE_LIST:
            print(f"Adding Topology file: {topology_file}")
            with open(topology_file, "r", encoding="utf-8") as infile:
                self.topology_manager.add_topology(json.load(infile))

        topology = self.topology_manager.get_topology()

        for node in topology.get_nodes():
            topology_id = self.topology_manager.get_domain_name(node.id)

            if node.id in (
                "urn:sdx:node:amlight.net:A1",
                "urn:sdx:node:amlight.net:B1",
                "urn:sdx:node:amlight.net:B2",
            ):
                self.assertEqual(
                    topology_id, "urn:ogf:network:sdx:topology:amlight.net"
                )

            if node.id in (
                "urn:ogf:network:sdx:node:sax:A1",
                "urn:ogf:network:sdx:node:sax:B1",
                "urn:ogf:network:sdx:node:sax:B2",
                "urn:ogf:network:sdx:node:sax:B3",
            ):
                self.assertEqual(topology_id, "urn:ogf:network:sdx:topology:sax.net")

            if node.id in (
                "urn:ogf:network:sdx:node:zaoxi:A1",
                "urn:ogf:network:sdx:node:zaoxi:B1",
                "urn:ogf:network:sdx:node:zaoxi:B2",
            ):
                self.assertEqual(topology_id, "urn:ogf:network:sdx:topology:zaoxi.net")


if __name__ == "__main__":
    unittest.main()
