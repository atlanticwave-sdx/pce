import unittest

import networkx as nx

from sdx_pce.utils.random_topology_generator import RandomTopologyGenerator


class RandomTopologyGeneratorTest(unittest.TestCase):
    def setUp(self):
        self.generator = RandomTopologyGenerator(num_node=5)

    def test_generate_graph(self):
        graph = self.generator.generate_graph(plot=False)
        self.assertIsInstance(graph, nx.Graph)
        self.assertEqual(len(graph.nodes), 5)

    def test_link_property_assign(self):
        graph = nx.Graph()
        graph.add_nodes_from([1, 2, 3])
        graph.add_edges_from([(1, 2), (2, 3)])
        self.generator.set_graph(graph)
        self.generator.link_property_assign()
        self.assertIsNotNone(self.generator.get_latency_list())

    def test_nodes_connected(self):
        graph = nx.Graph()
        graph.add_nodes_from([1, 2, 3])
        graph.add_edges_from([(1, 2), (2, 3)])
        self.assertTrue(self.generator.nodes_connected(graph, 1, 2))
        self.assertFalse(self.generator.nodes_connected(graph, 1, 3))

    def test_get_connectivity(self):
        graph = self.generator.generate_graph(plot=False)
        self.assertGreaterEqual(self.generator.get_connectivity(), 2)


if __name__ == "__main__":
    unittest.main()
