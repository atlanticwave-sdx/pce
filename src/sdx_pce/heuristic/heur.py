import argparse

# importing the module
from datetime import datetime

import numpy as np
import prtpy

from sdx_pce.load_balancing.te_solver import TESolver
from sdx_pce.models import PceConnectionRequest, TrafficMatrix
from sdx_pce.utils.random_connection_generator import RandomConnectionGenerator
from sdx_pce.utils.random_topology_generator import RandomTopologyGenerator


def random_graph(n, p, m):
    """
    Generate a random graph and a traffic matrix
    :param n: number of nodes
    :param p: probability that a link exist between a pair of nodes
    :param m: number of connections in the request
    """
    graph_generator = RandomTopologyGenerator(n, p)
    graph = graph_generator.generate_graph()

    tm_generator = RandomConnectionGenerator(n)
    tm = tm_generator.generate(m, 500, 2000, 80, 100).connection_requests
    matrix = []
    for rq in tm:
        query = []
        query.append(rq.source)
        query.append(rq.destination)
        query.append(rq.required_bandwidth)
        query.append(rq.required_latency)
        matrix.append(tuple(query))
    return graph, matrix


def matrix_to_connection(matrix):
    """
    Convert the plain traffic matrix to TrafficMatrix model used by TESolver as input
    """
    traffic_matrix = TrafficMatrix(connection_requests=[])
    for rq in matrix:
        request = PceConnectionRequest(
            source=rq[0],
            destination=rq[1],
            required_bandwidth=rq[2],
            required_latency=rq[3],
        )
        traffic_matrix.connection_requests.append(request)
    return traffic_matrix


class TEGroupSolver:
    """ "
    Class for a connection (TE matrix) splitting based heuristic solver
    Grouping heuristic, descending sorting on the request bandwidth, 1. linear: largest first 2. Geometry: (interval [B/2^(r+1), B/2^2]) 3. kk
    """

    def __init__(self, topology, tm, cost, objective):
        self.tm = tm
        self.topology = topology
        self.cost = cost
        self.objective = objective
        self.pad = 0

    def connection_split(self, s, k):
        """entry function on different spliting algorithms
        :param s: algorithm of choice
        :param k: number of groups
        """
        s_tm = self.sort_tm()
        if s == 0:
            partition_tm = self.linear_partition(s_tm, k)
        if s == 1:
            partition_tm = self.geometry_partition(s_tm, k)
        if s == 2:
            partition_tm = self.kk_partition(s_tm, k)

        return partition_tm

    def sort_tm(self):
        """Sorting the tm ascendingly on the bandwidth
        return: np array, dtype = {'names':['src', 'dest', 'bandwidth', 'latency'], 'formats':[int, int, float, float]}
        """

        # sorted_tm = np.sort(np.asarray(self.tm), axis = -1)
        print(f"tm shape: {np.shape(self.tm)}")
        # dtype = ('src', int),('dest', int), ('bandwidth', float), ('latency', float)
        dtype = {
            "names": ["src", "dest", "bandwidth", "latency"],
            "formats": [int, int, float, float],
        }
        np_tm = np.array(self.tm, dtype=dtype)
        # sorted_tm = np_tm[np_tm[:,2].argsort()]
        sorted_tm = np.sort(np_tm, order="bandwidth")
        print(f"sorted_tm type:{type(sorted_tm)}: shape={np.shape(sorted_tm)}")
        # print(sorted_tm)
        return sorted_tm

    def linear_partition(self, sorted_tm, k):
        """
        evenly partition into k groups
        :param k: number of groups
        """
        partition_tm = []
        num_connection = sorted_tm.shape[0]
        num, mod = divmod(num_connection, k)
        print(f"num:{num},mod:{mod},pad:{k-mod}")

        pad = 0
        for i in range(k):
            if i < mod:
                partition = sorted_tm[i * num + pad : (i + 1) * num + 1 + pad]
                print(f"{i}:{i*num+pad} : {(i+1)*num+1+pad}: {len(partition)}")
                pad = 1
            else:
                partition = sorted_tm[i * num + mod : (i + 1) * num + mod]
                print(f"{i}:{i*num+mod} : {(i+1)*num+mod}")
            partition_tm.append(partition)
        # print(partition_tm)
        print(
            f"Linear tm partitioning:{k}:{num}:{mod}:shape={len(partition_tm)}:type={type(partition_tm)}"
        )
        return partition_tm

    def geometry_partition(self, sorted_tm, k):
        """
        geometrical partition into k groups
        :param k: number of groups
        """
        tm_size = len(sorted_tm)
        min_b = sorted_tm[0]["bandwidth"] - 0.5
        max_b = sorted_tm[tm_size - 1]["bandwidth"] + 0.5
        delta_b = max_b - min_b
        r = []
        partition_list = []
        r.append(min_b)
        for i in range(k):
            # v = int(tm_size / (2 ** (i + 1)))
            ri = delta_b / (2 ** (k - i - 1))
            r.append(min_b + ri)
            partition = []
            partition_list.append(partition)
        # print(f"r={r}")
        for connection in sorted_tm:
            for i in range(k):
                if connection[2] >= r[i] and connection[2] < r[i + 1]:
                    partition_list[i].append(connection)

        partition_tm = []
        for partition in partition_list:
            if len(partition) != 0:
                partition_tm.append(partition)
            print(f"partion:shape={len(partition)}:type={type(partition)}")
        # print(partition_tm)
        print(
            f"Geometry tm partitioning:{k}:shape={len(partition_tm)}:type={type(partition_tm)}"
        )
        return partition_tm

    def kk_partition(self, sorted_tm, k):
        """
        using the KK multiwau number partitioning algorithm to partition into k groups
        :param k: number of groups
        """
        map_items = {}
        for connection in sorted_tm:
            # print(connection)
            # print(type(tuple(connection)))
            map_items[tuple(connection)] = connection[2]  # {connection:bw}
        partition_tm = prtpy.partition(
            algorithm=prtpy.partitioning.kk, numbins=k, items=map_items
        )
        # print(partition_tm)
        print(
            f"kk tm partitioning:{k} :shape={len(partition_tm)}:type={type(partition_tm)}"
        )
        return partition_tm

    def solve(self, partition_tm):
        partition_shape = len(partition_tm)
        graph = self.topology
        # print("Partition_shape="+str(partition_shape))
        # print(partition_tm)
        final_result = 0
        final_ordered_paths = []
        for i in range(partition_shape - 1, -1, -1):
            partition = partition_tm[i]

            # print(partition)
            tm = matrix_to_connection(partition)
            print(f"length:{len(tm.connection_requests)}")
            solver = TESolver(graph, tm, self.cost, self.objective)
            ordered_paths = solver.solve()
            graph = solver.update_graph(graph, ordered_paths)
            final_result = final_result + ordered_paths.cost
            final_ordered_paths.append(ordered_paths.connection_map)
        return final_ordered_paths, final_result

    def disjoint_path(self, connection):
        # Prime path:solver
        # prune the graph
        # Backup path: solver again
        # path translator -> dict.
        pass


if __name__ == "__main__":
    parse = argparse.ArgumentParser()
    parse.add_argument(
        "-t",
        dest="te_file",
        required=False,
        help="Input file for the connections or traiffc matrix, e.g. c connection.json. Required.",
        type=str,
    )
    parse.add_argument(
        "-n",
        dest="topology_file",
        required=False,
        help="Input file for the network topology, e.g. t topology.json. Required.",
        type=str,
    )
    parse.add_argument(
        "-c", dest="c", required=False, default=0, help="Link cost definition", type=int
    )
    parse.add_argument(
        "-b",
        dest="b",
        required=False,
        default=0,
        help="Objective: MinCost or Load balancing",
        type=int,
    )
    parse.add_argument(
        "-m",
        dest="m",
        required=False,
        default=5,
        help="Number of connections in the random TE",
        type=int,
    )
    parse.add_argument(
        "-a",
        dest="alg",
        default=0,
        help="Flag for different grouping heuristic algorithms, default is the linear partition",
        type=int,
    )
    parse.add_argument("-g", dest="group", default=2, help="number of groups", type=int)
    parse.add_argument(
        "-o",
        dest="result",
        default="OUTPUT.txt",
        help="Output file, e.g. o result.txt. If this option is not given, assume standard output.",
        type=str,
    )

    parse.print_help()
    args = parse.parse_args()
    # result(args.te_file,args.node_name , args.result)

    if args.topology_file is not None:
        if args.te_file is not None:
            # graph, tm = dot_file(args.topology_file, args.te_file)
            print("Supporting dot file later!")
            exit()
        else:
            print("Missing the TE file!")
            exit()
    else:
        p = 0.2
        n = 25

        graph, tm = random_graph(n, p, args.m)

    if args.group > args.m:
        print("Group cannot be greater the number of connections!")
        exit(0)

    te = TEGroupSolver(graph, tm, args.c, args.b)
    start = datetime.now()
    partition_tm = te.connection_split(args.alg, args.group)
    end = datetime.now()
    # print elapsed time in microseconds
    print("Elapsed", (end - start).total_seconds(), "s")

    ordered_paths, result = te.solve(partition_tm)

    print(f"path: {ordered_paths}")
    print(f"Optimal: {result}")
