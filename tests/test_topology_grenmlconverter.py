import unittest

from sdx.pce.topology.manager import TopologyManager
from sdx.pce.topology.grenmlconverter import GrenmlConverter


TOPOLOGY_AMLIGHT = "./tests/data/amlight.json"


class TestTopologyGRENMLConverter(unittest.TestCase):
    def setUp(self):
        self.manager = TopologyManager()  # noqa: E501
        self.handler = self.manager.handler
        self.handler.topology_file_name(TOPOLOGY_AMLIGHT)
        self.handler.import_topology()

    def tearDown(self):
        pass

    def testGrenmlConverter(self):
        try:
            print("Test Topology Converter")
            print(self.handler.topology)
            converter = GrenmlConverter(self.handler.topology)
            converter.read_topology()
            print(converter.get_xml_str())
        except Exception as e:
            print(e)
            return False
        return True
