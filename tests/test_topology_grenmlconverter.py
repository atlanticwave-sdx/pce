import pathlib
import unittest

from sdx.pce.topology.manager import TopologyManager
from sdx.pce.topology.grenmlconverter import GrenmlConverter


class GrenmlConverterTests(unittest.TestCase):
    """
    Tests for GrenmlConverter.
    """

    TEST_DATA_DIR = pathlib.Path(__file__).parent.joinpath("data")
    AMLIGHT_TOPOLOGY_FILE = TEST_DATA_DIR.joinpath("amlight.json")

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_grenml_converter_amlight(self):
        manager = TopologyManager()

        # TODO: this does not raise errors when it should (such as
        # when the input file is not present). Make the necessary
        # change in datamodel's TopologyHandler class.
        manager.handler.topology_file_name(self.AMLIGHT_TOPOLOGY_FILE)
        manager.handler.import_topology()

        print(f"Topology: {manager.handler.topology}")
        self.assertIsNotNone(manager.handler.topology, "No topology could be read")

        converter = GrenmlConverter(manager.handler.topology)
        print(f"GrenmlConverter: {converter}")
        self.assertIsNotNone(converter, "Could not create GRENML converter")

        converter.read_topology()
        xml = converter.get_xml_str()
        print(f"XML: {xml}")
        self.assertIsNotNone(xml)
