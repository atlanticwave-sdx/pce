import unittest

from sdx_pce.utils.random_connection_generator import RandomConnectionGenerator


class RandomConnectionGeneratorTest(unittest.TestCase):
    def setUp(self):
        self.generator = RandomConnectionGenerator(20)

    def test_generate(self):
        querynum = 3
        l_bw = 100
        u_bw = 1000
        l_lat = 1000
        u_lat = 1500
        seed = 2022

        traffic_matrix = self.generator.generate(
            querynum, l_bw, u_bw, l_lat, u_lat, seed
        )

        # Assert that the generated traffic matrix has the correct number of requests
        self.assertEqual(len(traffic_matrix.connection_requests), querynum)

        # Assert that each request has the correct bandwidth and latency values
        for request in traffic_matrix.connection_requests:
            self.assertGreaterEqual(request.required_bandwidth, l_bw)
            self.assertLessEqual(request.required_bandwidth, u_bw)
            self.assertGreaterEqual(request.required_latency, l_lat)
            self.assertLessEqual(request.required_latency, u_lat)

    def test_lognormal(self):
        # Add test cases for the lognormal method if needed
        pass

    def test_random(self):
        # Add test cases for the random method if needed
        pass


if __name__ == "__main__":
    unittest.main()
