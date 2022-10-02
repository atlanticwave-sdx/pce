import unittest
import dijsktra

graph4 = {
    "A": {"B": [3, 4], "C": 8},
    "B": {"C": 2, "D": [5, 6]},
    "C": {"B": 2, "D": 2},
    "D": {"B": [5, 6],"C": 2}
}
class Testdij(unittest.TestCase):

    def test_dijnew(self):
        result = dijsktra.dijnew(graph4, "A", "D")
        self.assertEqual(result, ['A', 'B', 'C', 'D'])


if __name__ == "__main__":
    unittest.main()