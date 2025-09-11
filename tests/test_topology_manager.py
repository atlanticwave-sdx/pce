import copy
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
    TOPOLOGY_FILE_LIST_UPDATE = [TestData.TOPOLOGY_FILE_SAX_2_UPDATE]
    TOPOLOGY_V2_FILE_LIST_UPDATE = [TestData.TOPOLOGY_FILE_SAX_V2_UPDATE]

    LINK_ID = "urn:sdx:link:amlight.net:B1-B2"
    INTER_LINK_ID = "urn:sdx:link:zaoxi.net:A1-B2"

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

        # test update topology
        for topology_file in self.TOPOLOGY_FILE_LIST_v2:
            topology_data = json.loads(pathlib.Path(topology_file).read_text())
            topology_data["version"] += 1
            self.topology_manager.update_topology(topology_data)

        topology = self.topology_manager.get_topology()

        self.assertIsInstance(topology.to_dict(), dict)

        self.assertEqual(len(topology.nodes), 8)

        self.assertEqual(len(topology.links), 10)

        interdomain_links = [
            link for link in topology.links if "urn:sdx:link:interdomain:" in link.id
        ]
        self.assertEqual(len(interdomain_links), 4)

        print(f"Writing result to {self.TOPOLOGY_OUT}")
        pathlib.Path(self.TOPOLOGY_OUT).write_text(
            json.dumps(topology.to_dict(), indent=4)
        )

    def test_get_topology_dict(self):
        print("Test Topology get_topology_dict")

        self.test_merge_topology()

        topology_dict = self.topology_manager.get_topology_dict()

        self.assertIsInstance(topology_dict, dict)
        self.assertIn("nodes", topology_dict)
        self.assertIn("links", topology_dict)

        print(f"Topology dict: {json.dumps(topology_dict, indent=4)}")

    def test_get_topology_map(self):
        print("Test Topology get_topology_map")

        self.test_merge_topology()

        topology_map = self.topology_manager.get_topology_map()

        self.assertIsInstance(topology_map, dict)

        self.assertTrue(len(topology_map) == 3)

    def test_get_topology_map_dict(self):
        print("Test Topology get_topology_map_dict")

        self.test_merge_topology()

        topology_map = self.topology_manager.get_topology_map()

        topology_map_dict = {}

        for key, value in topology_map.items():
            topology_map_dict[key] = value.to_dict()

        self.assertTrue(len(topology_map_dict) == 3)

        # print(f"Topology map dict: {json.dumps(topology_map_dict, indent=4)}")

    def test_topology_diff(self):
        print("Test Topology Diff")

        # Create the initial topology
        self.test_merge_topology()

        # Get the old topology
        old_topology = copy.deepcopy(self.topology_manager.get_topology())

        # Modify the topology by removing a link
        new_links = []
        for link in self.topology_manager.get_topology().links:
            if link.id != self.LINK_ID:
                new_links.append(link)

        self.topology_manager.get_topology().links = new_links
        self.assertEqual(len(new_links), 13)

        # Modify the topology by setting a link's status to "down"
        link = self.topology_manager.update_link_property(
            self.INTER_LINK_ID, "status", "down"
        )
        self.assertEqual(link.status, "down")

        # Get the new topology
        new_topology = self.topology_manager.get_topology()

        # Get the topology diff
        _, _, removed_links, _, _, _ = self.topology_manager.topology_diff(
            old_topology, new_topology
        )

        print(
            f" total removed links: {[removed_link.id for removed_link in removed_links]}"
        )

        # Check the removed_links list
        self.assertIn(self.LINK_ID, [link.id for link in removed_links])

        # Check the removed_links list for the "down" status
        for link in removed_links:
            if link.id == self.INTER_LINK_ID:
                down_link = new_topology.get_link_by_id(link.id)
                break
        self.assertIsNotNone(down_link)
        self.assertEqual(down_link.status, "down")

    def test_update_topology_v2(self):
        print("Test Topology Update!")

        self.test_merge_topology_v2()

        print(f"len of links: {len(self.topology_manager.get_topology().links)}")

        for topology_file in self.TOPOLOGY_FILE_LIST_UPDATE:
            print(f"Updating topology: {topology_file}")
            topology_data = json.loads(pathlib.Path(topology_file).read_text())
            (
                removed_nodes_list,
                added_nodes_list,
                removed_links_list,
                added_links_list,
                uni_ports_up_to_down,
                uni_ports_down_to_up,
            ) = self.topology_manager.update_topology(topology_data)

        self.assertEqual(len(removed_links_list), 1)
        self.assertEqual(len(added_links_list), 7)

    def test_update_topology_uni_v2(self):
        print("Test Topology Update!")

        self.test_merge_topology_v2()

        print(f"len of links: {len(self.topology_manager.get_topology().links)}")

        for topology_file in self.TOPOLOGY_V2_FILE_LIST_UPDATE:
            print(f"Updating topology: {topology_file}")
            topology_data = json.loads(pathlib.Path(topology_file).read_text())
            (
                removed_nodes_list,
                added_nodes_list,
                removed_links_list,
                added_links_list,
                uni_ports_up_to_down,
                uni_ports_down_to_up,
            ) = self.topology_manager.update_topology(topology_data)

        self.assertEqual(len(uni_ports_up_to_down), 1)
        self.assertEqual(len(removed_links_list), 2)

    def test_grenml_converter(self):
        print("Test Topology GRENML Converter")
        self.test_merge_topology()
        converter = GrenmlConverter(self.topology_manager.get_topology())
        converter.read_topology()
        xml = converter.get_xml_str()
        print(f"xml: {xml}")
        self.assertIsNotNone(xml)

    def test_generate_graph_v2(self):
        print("Test Topology Graph")
        self.test_merge_topology_v2()
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
