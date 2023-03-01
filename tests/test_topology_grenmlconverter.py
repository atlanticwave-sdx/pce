import pathlib
import unittest

from sdx.pce.topology.grenmlconverter import GrenmlConverter
from sdx.pce.topology.manager import TopologyManager


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
        manager.topology_handler.topology_file_name(self.AMLIGHT_TOPOLOGY_FILE)
        manager.topology_handler.import_topology()

        print(f"Topology: {manager.topology_handler.topology}")
        self.assertIsNotNone(
            manager.topology_handler.topology, "No topology could be read"
        )

        converter = GrenmlConverter(manager.topology_handler.topology)
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
