import json
import pathlib
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
    TOPOLOGY_FILE_LIST_v2 = [
        TestData.TOPOLOGY_FILE_AMLIGHT_v2,
        TestData.TOPOLOGY_FILE_ZAOXI_v2,
        TestData.TOPOLOGY_FILE_SAX_v2,
    ]
    TOPOLOGY_FILE_LIST_UPDATE = [TestData.TOPOLOGY_FILE_ZAOXI]

    LINK_ID = "urn:sdx:link:amlight:A1-B2"
    INTER_LINK_ID = "urn:sdx:link:nni:Miami-Sanpaolo"

    def setUp(self):
        self.topology_manager = TopologyManager()

    def tearDown(self):
        self.topology_manager = None

    def test_merge_topology(self):
        print("Test Topology Merge!")

        for topology_file in self.TOPOLOGY_FILE_LIST:
            print(f"Adding Topology file: {topology_file}")
            topology_data = json.loads(pathlib.Path(topology_file).read_text())
            self.topology_manager.add_topology(topology_data)

        topology = self.topology_manager.get_topology()

        self.assertIsInstance(topology.to_dict(), dict)

        print(f"Writing result to {self.TOPOLOGY_OUT}")
        pathlib.Path(self.TOPOLOGY_OUT).write_text(
            json.dumps(topology.to_dict(), indent=4)
        )

    def test_merge_topology_v2(self):
        for topology_file in self.TOPOLOGY_FILE_LIST_v2:
            topology_data = json.loads(pathlib.Path(topology_file).read_text())
            self.topology_manager.add_topology(topology_data)

        topology = self.topology_manager.get_topology()

        self.assertIsInstance(topology.to_dict(), dict)

        self.assertEqual(len(topology.nodes), 8)

        self.assertEqual(len(topology.links), 10)

        interdomain_links = [
            link for link in topology.links if "urn:sdx:link:interdomain:" in link.id
        ]
        self.assertEqual(len(interdomain_links), 4)

    def test_update_topology(self):
        print("Test Topology Update!")

        self.test_merge_topology()

        for topology_file in self.TOPOLOGY_FILE_LIST_UPDATE:
            print(f"Updating topology: {topology_file}")
            topology_data = json.loads(pathlib.Path(topology_file).read_text())
            self.topology_manager.add_topology(topology_data)

        topology = self.topology_manager.get_topology()

        self.assertIsInstance(topology.to_dict(), dict)

        pathlib.Path(self.TOPOLOGY_OUT).write_text(
            json.dumps(topology.to_dict(), indent=4)
        )

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

        topology = self.topology_manager.get_topology()

        self.assertIsInstance(topology.to_dict(), dict)

        pathlib.Path(self.TOPOLOGY_OUT).write_text(
            json.dumps(topology.to_dict(), indent=4)
        )

    def test_link_property_update_json(self):
        print("Test Topology JSON Link Property Update!")

        topology_data = json.loads(pathlib.Path(self.TOPOLOGY_IN).read_text())

        self.topology_manager.update_element_property_json(
            topology_data, "links", self.LINK_ID, "latency", 20
        )

        self.assertIsInstance(topology_data, dict)

        pathlib.Path(self.TOPOLOGY_OUT).write_text(json.dumps(topology_data, indent=4))

    def test_get_domain_name(self):
        """
        Test that TopologyManager.get_domain_name() works as expected.
        """
        for topology_file in self.TOPOLOGY_FILE_LIST:
            print(f"Adding Topology file: {topology_file}")
            topology_data = json.loads(pathlib.Path(topology_file).read_text())
            self.topology_manager.add_topology(topology_data)

        topology = self.topology_manager.get_topology()

        for node in topology.nodes:
            topology_id = self.topology_manager.get_domain_name(node.id)

            if node.id in (
                "urn:sdx:node:amlight.net:A1",
                "urn:sdx:node:amlight.net:B1",
                "urn:sdx:node:amlight.net:B2",
            ):
                self.assertEqual(topology_id, "urn:sdx:topology:amlight.net")

            if node.id in (
                "urn:sdx:node:sax:A1",
                "urn:sdx:node:sax:B1",
                "urn:sdx:node:sax:B2",
                "urn:sdx:node:sax:B3",
            ):
                self.assertEqual(topology_id, "urn:sdx:topology:sax.net")

            if node.id in (
                "urn:sdx:node:zaoxi:A1",
                "urn:sdx:node:zaoxi:B1",
                "urn:sdx:node:zaoxi:B2",
            ):
                self.assertEqual(topology_id, "urn:sdx:topology:zaoxi.net")


if __name__ == "__main__":
    unittest.main()
