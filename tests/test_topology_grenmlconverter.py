import unittest

from sdx_datamodel.parsing.topologyhandler import TopologyHandler

from sdx_pce.topology.grenmlconverter import GrenmlConverter
from sdx_pce.topology.manager import TopologyManager

from . import TestData


class GrenmlConverterTests(unittest.TestCase):
    """
    Tests for GrenmlConverter.
    """

    # TEST_DATA_DIR = pathlib.Path(__file__).parent / "data"
    # AMLIGHT_TOPOLOGY_FILE = TEST_DATA_DIR / "topologies" / "amlight.json"

    def test_grenml_converter_amlight(self):
        TopologyManager()

        # TODO: this does not raise errors when it should (such as
        # when the input file is not present). Make the necessary
        # change in datamodel's TopologyHandler class.
        topology = TopologyHandler().import_topology(TestData.TOPOLOGY_FILE_AMLIGHT)

        print(f"Topology: {topology}")
        self.assertIsNotNone(topology, "No topology could be read")

        converter = GrenmlConverter(topology)
        print(f"GrenmlConverter: {converter}")
        self.assertIsNotNone(converter, "Could not create GRENML converter")

        converter.read_topology()
        xml = converter.get_xml_str()
        print(f"XML: {xml}")
        self.assertIsNotNone(xml)

    def test_grenml_converter_bad_input(self):
        # Ensure that GrenmlConverter fails when no topology input is
        # given.
        with self.assertRaises(AttributeError):
            GrenmlConverter(None)

        with self.assertRaises(AttributeError):
            GrenmlConverter("")

        with self.assertRaises(AttributeError):
            GrenmlConverter("{'dummy':'dummy'}")

    def test_grenml_converter_empty_topology(self):
        # Ensure that GrenmlConverter handles empty topology correctly.
        empty_topology = {}
        converter = GrenmlConverter(empty_topology)
        converter.read_topology()
        xml = converter.get_xml_str()
        print(f"XML for empty topology: {xml}")
        self.assertIsNotNone(xml)
        self.assertIn("<topology>", xml)
        self.assertIn("</topology>", xml)

    def test_grenml_converter_invalid_topology(self):
        # Ensure that GrenmlConverter handles invalid topology correctly.
        invalid_topology = {"invalid": "data"}
        converter = GrenmlConverter(invalid_topology)
        with self.assertRaises(Exception):
            converter.read_topology()

    def test_grenml_converter_partial_topology(self):
        # Ensure that GrenmlConverter handles partial topology correctly.
        partial_topology = {"nodes": [{"id": "node1"}], "links": []}
        converter = GrenmlConverter(partial_topology)
        converter.read_topology()
        xml = converter.get_xml_str()
        print(f"XML for partial topology: {xml}")
        self.assertIsNotNone(xml)
        self.assertIn('<node id="node1"/>', xml)
        self.assertIn("<topology>", xml)
        self.assertIn("</topology>", xml)

    def test_grenml_converter_add_nodes(self):
        # Ensure that GrenmlConverter can add nodes correctly.
        topology = {"nodes": [], "links": []}
        converter = GrenmlConverter(topology)
        nodes = [{"id": "node1"}, {"id": "node2"}]
        converter.add_nodes(nodes)
        xml = converter.get_xml_str()
        print(f"XML after adding nodes: {xml}")
        self.assertIn('<node id="node1"/>', xml)
        self.assertIn('<node id="node2"/>', xml)

    def test_grenml_converter_add_links(self):
        # Ensure that GrenmlConverter can add links correctly.
        topology = {"nodes": [{"id": "node1"}, {"id": "node2"}], "links": []}
        converter = GrenmlConverter(topology)
        links = [{"source": "node1", "target": "node2"}]
        converter.add_links(links)
        xml = converter.get_xml_str()
        print(f"XML after adding links: {xml}")
        self.assertIn('<link source="node1" target="node2"/>', xml)
