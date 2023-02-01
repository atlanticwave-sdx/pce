import unittest
import json
from networkx import MultiGraph, Graph
import matplotlib.pyplot as plt
import networkx as nx

from sdx.datamodel import parsing
from sdx.datamodel import topologymanager

from sdx.datamodel import validation
from sdx.datamodel.validation.topologyvalidator import TopologyValidator
from sdx.datamodel.parsing.topologyhandler import TopologyHandler
from sdx.datamodel.topologymanager.manager import TopologyManager
from sdx.datamodel.topologymanager.grenmlconverter import GrenmlConverter
from sdx.datamodel.parsing.exceptions import DataModelException


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

    def setUp(self):
        self.manager = TopologyManager()

    def tearDown(self):
        pass

    def testMergeTopology(self):
        print("Test Topology Merge!")
        try:
            for topology_file in topology_file_list_3:
                with open(topology_file, "r", encoding="utf-8") as data_file:
                    data = json.load(data_file)
                print("Adding Topology:" + topology_file)
                self.manager.add_topology(data)
            with open(self.TOPOLOGY_OUT, "w") as t_file:
                json.dump(self.manager.topology.to_dict(), t_file, indent=4)

        except DataModelException as e:
            print(e)
            return False
        return True

    def testUpdateTopology(self):
        print("Test Topology Update!")
        try:
            self.testMergeTopology()
            for topology_file in self.TOPOLOGY_FILE_LIST_UPDATE:
                with open(topology_file, "r", encoding="utf-8") as data_file:
                    data = json.load(data_file)
                print("Updating Topology:" + topology_file)
                self.manager.update_topology(data)

            with open(self.TOPOLOGY_OUT, "w") as t_file:
                json.dump(self.manager.topology.to_dict(), t_file, indent=4)
            graph = self.manager.generate_graph()
            # pos = nx.spring_layout(graph, seed=225)  # Seed for reproducible layout
            nx.draw(graph, with_labels=True)
            plt.savefig(self.TOPOLOGY_png)
        except DataModelException as e:
            print(e)
            return False
        return True

    def testGrenmlConverter(self):
        try:
            print("Test Topology GRENML Converter")
            self.testMergeTopology()
            converter = GrenmlConverter(self.manager.get_topology())
            converter.read_topology()
            print(converter.get_xml_str())
        except DataModelException as e:
            print(e)
            return False
        return True

    def testGenerateGraph(self):
        try:
            print("Test Topology Graph")
            self.testMergeTopology()
            graph = self.manager.generate_graph()
            # pos = nx.spring_layout(graph, seed=225)  # Seed for reproducible layout
            nx.draw(graph, with_labels=True)
            plt.savefig(self.TOPOLOGY_PNG)
        except DataModelException as e:
            print(e)
            return False
        return True

    def testLinkPropertyUpdate(self):
        print("Test Topology Link Property Update!")
        try:
            self.testMergeTopology()
            self.manager.update_link_property(link_id, "latency", 8)
            self.manager.update_link_property(inter_link_id, "latency", 8)
            with open(self.TOPOLOGY_OUT, "w") as t_file:
                json.dump(self.manager.topology.to_dict(), t_file, indent=4)
        except DataModelException as e:
            print(e)
            return False
        return True

    def testLinkPropertyUpdateJson(self):
        print("Test Topology JSON Link Property Update!")
        try:
            with open(self.TOPOLOGY_IN, "r", encoding="utf-8") as data_file:
                data = json.load(data_file)
                self.manager.update_element_property_json(
                    data, "links", link_id, "latency", 20
                )
            with open(self.TOPOLOGY_OUT, "w") as t_file:
                json.dump(data, t_file, indent=4)
        except DataModelException as e:
            print(e)
            return False
        return True


if __name__ == "__main__":
    unittest.main()
