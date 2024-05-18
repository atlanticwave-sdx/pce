import unittest
from sdx_pce.utils.functions import dijnew, backup_path

class TestDijnew(unittest.TestCase):
    def test_shortest_path(self):
        graph = {
            'A': {'B': 2, 'C': 4},
            'B': {'A': 2, 'C': 1, 'D': 4},
            'C': {'A': 4, 'B': 1, 'D': 3},
            'D': {'B': 4, 'C': 3}
        }
        start_node = 'A'
        end_node = 'D'
        expected_path = ['A', 'B', 'D']
        
        result = dijnew(graph, start_node, end_node)
        print(result)
        
        self.assertEqual(result, expected_path)
    
    def test_unreachable_path(self):
        graph = {
            'A': {'B': 2, 'C': 4},
            'B': {'A': 2, 'C': 1},
            'C': {'A': 4, 'B': 1},
            'D': {'E': 4},
            'E': {'D': 4}
        }
        start_node = 'A'
        end_node = 'D'
        expected_path = []
        
        result = dijnew(graph, start_node, end_node)

        print(result)

        
        self.assertEqual(result, expected_path)

    def test_backup_path(self):
        graph = {
            'A': {'B': 2, 'C': 4},
            'B': {'A': 2, 'C': 1, 'D': 4},
            'C': {'A': 4, 'B': 1, 'D': 3},
            'D': {'B': 4, 'C': 3}
        }
        start_node = 'A'
        end_node = 'D'
        expected_path = ['A', 'C', 'D']
        
        result = backup_path(graph, start_node, end_node)

        print(result)
        
        self.assertEqual(result, expected_path)

if __name__ == '__main__':
    unittest.main()