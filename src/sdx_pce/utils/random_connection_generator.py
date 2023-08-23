import numpy as np

from sdx_pce.models import ConnectionRequest, TrafficMatrix


class RandomConnectionGenerator:
    def __init__(self, num_nodes):
        """
        :param num_nodes: Number of nodes of the topology.
        """
        self.num_nodes = num_nodes

    # Output: list of tuples of request
    def generate(self, querynum, l_bw, u_bw, l_lat, u_lat, seed=2022) -> TrafficMatrix:
        """
        Create a random traffic matrix.

        :param querynum: Number of connections.

        :return: A connection matrix.  A connection matrix is list of
                 connections, and each item in the list is of the
                 format (source, destination, bandwidth, latency).
        """
        np.random.seed(seed)
        traffic_matrix = TrafficMatrix(connection_requests=[])

        bw = self.lognormal((l_bw + u_bw) / 2.0, 1, querynum)
        if querynum <= self.num_nodes:
            for i in range(querynum):
                source = np.random.randint(1, (self.num_nodes + 1) / 2.0)
                destination = np.random.randint(
                    (self.num_nodes + 1) / 2.0, self.num_nodes
                )
                required_bandwidth = bw[i]
                required_latency = np.random.randint(l_lat, u_lat)

                request = ConnectionRequest(
                    source=source,
                    destination=destination,
                    required_bandwidth=required_bandwidth,
                    required_latency=required_latency,
                )

                traffic_matrix.connection_requests.append(request)
        else:
            for i in range(querynum):
                source = np.random.randint(0, self.num_nodes)
                destination = np.random.randint(0, self.num_nodes)
                while destination == source:
                    destination = np.random.randint(0, self.num_nodes)
                # query.append(np.random.randint(l_bw, u_bw))
                required_bandwidth = bw[i]
                required_latency = np.random.randint(l_lat, u_lat)

                request = ConnectionRequest(
                    source=source,
                    destination=destination,
                    required_bandwidth=required_bandwidth,
                    required_latency=required_latency,
                )

                traffic_matrix.connection_requests.append(request)

        return traffic_matrix

    def lognormal(self, mu, sigma, size):
        normal_std = 0.5
        # normal_std = np.sqrt(np.log(1 + (sigma/mu)**2))
        normal_mean = np.log(mu) - normal_std**2 / 2
        return np.random.lognormal(normal_mean, normal_std, size)

    def random(self, min, mx, size):
        return np.random.randint(min, max, 1000)


# tm = RandomConnectionGenerator(20)
# connection = tm.generate(3, 100, 1000, 1000, 1500, 2022)
