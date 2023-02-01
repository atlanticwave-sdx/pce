import unittest

from sdx.pce.topology.manager import TopologyManager
from sdx.pce.topology.grenmlconverter import GrenmlConverter


TOPOLOGY_AMLIGHT = "./tests/data/amlight.json"


class GrenmlConverterTests(unittest.TestCase):
    
    def setUp(self):
        pass
    
    def tearDown(self):
        pass

    def testGrenmlConverter(self):
        manager = TopologyManager()

        # TODO: this does not raise errors when it should (such as
        # when the input file is not present). Make the necessary
        # change in datamodel's TopologyHandler class.
        manager.handler.topology_file_name(TOPOLOGY_AMLIGHT)
        topology = manager.handler.import_topology()
        
        try:
            print("Test Topology Converter")
            print(f"Topology: {topology}")

            converter = GrenmlConverter(topology)
            self.assertIsNotNone(converter)

            converter.read_topology()
            xml = converter.get_xml_str()
            print(f"XML: {xml}")
            self.assertIsNotNone(xml)
            
        except Exception as e:
            print(e)
            return False
        return True
