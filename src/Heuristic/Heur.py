import argparse
import json

# importing the module
from datetime import datetime

import numpy as np
import prtpy

import Utility.global_name as global_name
from LoadBalancing.MC_Solver import runMC_Solver
from LoadBalancing.RandomTopologyGenerator import lbnxgraphgenerator
from LoadBalancing.TE_Solver import TE_Solver
from Utility.randomConnectionGenerator import RandomConnectionGenerator
from Utility.randomTopologyGenerator import RandomTopologyGenerator, dot_file


def random_graph(n, p, m):

    graph_generator = RandomTopologyGenerator(n, p)
    graph = graph_generator.generate_graph()

    tm_generator = RandomConnectionGenerator(n)
    tm = tm_generator.randomConnectionGenerator(m, 500, 2000, 50, 80)

    return graph, tm


class TE_Group_Solver:
    """
    Class for a connection (TE matrix) splitting based heuristic.

        1. Sequential: binpacking like heuristic:
           first-fit(any-fit)-decreasing, refined first fit (4
           classes): Online

        2. Grouping: k-shortest-path based grouping: (k, then all
           other pairs sharing a same link) : connection grouping:
           linear grouping (k largest items on); geometric grouping
           (interval [B/2^(r+1), B/2^2])
    """

    def __init__(self, topology, tm, cost, objective):
        self.tm = tm
        self.topology = topology
        self.cost = cost
        self.objective = objective
        self.pad = 0

    def ConnectionSplit(self, s, k):
        s_tm = self.sort_tm()
        if s == 0:
            partition_tm = self.linear_partition(s_tm, k)
        if s == 1:
            partition_tm = self.geometry_partition(s_tm, k)
        if s == 2:
            partition_tm = self.kk_partition(s_tm, k)

        return partition_tm

    def sort_tm(self):
        # sorted_tm = np.sort(np.asarray(self.tm), axis = -1)
        print("tm shape:" + str(np.shape(self.tm)))
        # dtype = ('src', int),('dest', int),
        # ('bandwidth', float), ('latency', float)
        dtype = {
            "names": ["src", "dest", "bandwidth", "latency"],
            "formats": [int, int, float, float],
        }
        np_tm = np.array(self.tm, dtype=dtype)
        # sorted_tm = np_tm[np_tm[:,2].argsort()]
        sorted_tm = np.sort(np_tm, order="bandwidth")
        # print(sorted_tm)
        return sorted_tm

    # sorted_tm: np array, dtype = {'names':['src', 'dest',
    # 'bandwidth', 'latency'], 'formats':[int, int, float, float]}
    def linear_partition(self, sorted_tm, k):
        partition_tm = []
        num_connection = sorted_tm.shape[0]
        num, mod = divmod(num_connection, k)
        # print(sorted_tm)

        if mod != 0:
            dtype = {
                "names": ["src", "dest", "bandwidth", "latency"],
                "formats": [int, int, float, float],
            }
            self.pad = k - mod
            pad_zeros = np.zeros((self.pad,), dtype=dtype)
            # print(pad_zeros)
            # print(type(pad_zeros))
            # print(sorted_tm.shape)
            partition = sorted_tm[0 : mod - 1]
            sorted_tm = np.append(pad_zeros, sorted_tm, axis=0)
            num = num + 1
        for i in range(0, num_connection + mod, num):
            partition = sorted_tm[i : i + num]
            partition_tm.append(partition)
        print(
            "Linear tm partitioning:"
            + str(k)
            + ":"
            + str(num)
            + ":"
            + str(mod)
            + ":shape="
            + str(np.shape(partition_tm))
        )
        # print(partition_tm)
        return partition_tm

    def geometry_partition(self, sorted_tm, k):
        tm_size = len(sorted_tm)
        r = []
        partition_list = []
        for i in range(k):
            v = tm_size / (2 ** (i + 1))
            r.append(v * global_name.Min_C_BW)
            partition = []
            partition_list.append(partition)
        r.append(0)
        print(r)
        for connection in sorted_tm:
            for i in range(k):
                if connection[2] >= r[k - i] and connection[2] < r[k - i - 1]:
                    partition_list[i].append(connection)

        partition_tm = []
        for partition in partition_list:
            if len(partition) != 0:
                partition_tm.append(partition)
        # print(partition_tm)
        print(
            "Geometry tm partitioning:"
            + str(k)
            + ":shape="
            + str(np.shape(partition_tm))
        )
        return partition_tm

    def kk_partition(self, sorted_tm, k):
        map_items = {}
        for connection in sorted_tm:
            # print(connection)
            # print(type(tuple(connection)))
            map_items[tuple(connection)] = connection[2]  # {connection:bw}
        partition_tm = prtpy.partition(
            algorithm=prtpy.partitioning.kk, numbins=k, items=map_items
        )
        print(f"kk tm partitioning: {k} :shape={np.shape(partition_tm)}")
        return partition_tm

    def solve(self, partition_tm):
        partition_shape = np.shape(partition_tm)
        graph = self.topology
        # print("Partition_shape="+str(partition_shape))
        # print(partition_tm)
        final_result = 0
        final_ordered_paths = []
        for i in range(partition_shape[0] - 1, -1, -1):
            # print("i="+str(i))
            if i == 0:
                partition = partition_tm[i][self.pad :]  # noqa: E203
            else:
                partition = partition_tm[i]
            print(partition)
            solver = TE_Solver(graph, partition, self.cost, self.objective)
            path, result = solver.solve()
            ordered_paths = solver.solution_translator(path, result)
            graph = solver.update_graph(graph, ordered_paths)
            final_result = final_result + result
            final_ordered_paths.append(ordered_paths)
        return final_ordered_paths, final_result

    def disjoint_path(self, connection):
        # Prime path:solver
        # prune the graph
        # Backup path: solver again
        # path translator -> dict.
        pass

    def Heuristic_CSP(self, connection, g):
        self.ConnectionSplit(0, 1)
        pathlist = {}
        cost = 0
        c = 1
        with open("./tests/data/splittedconnection.json") as f:
            connection = json.load(f)
        for query in connection:
            singleconnection = [query]
            with open("./tests/data/connection.json", "w") as json_file:
                data = singleconnection
                json.dump(data, json_file, indent=4)

            lbnxgraphgenerator(25, 0.4, data, g)

            solution = runMC_Solver()
            pathlist[str(c)] = solution[0]["1"]
            cost += solution[1]
            c += 1

        return [pathlist, cost]


if __name__ == "__main__":

    parse = argparse.ArgumentParser()
    parse.add_argument(
        "-t",
        dest="te_file",
        required=False,
        help="Input file for the connections or traiffc matrix, e.g. connection.json. Required.",  # noqa: E501
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
        "-c",
        dest="c",
        required=False,
        default=0,
        help="Link cost definition",
        type=int,
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
    parse.add_argument(
        "-g",
        dest="group",
        default=2,
        help="number of groups",
        type=int,
    )
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
            graph, tm = dot_file(args.topology_file, args.te_file)
        else:
            print("Missing the TE file!")
            exit()
    else:
        n = 25
        p = 0.2
        if args.m is None:
            print("Using default:" + "m=3")
            args.m = 3

        graph, tm = random_graph(n, p, args.m)

    te = TE_Group_Solver(graph, tm, args.c, args.b)
    start = datetime.now()
    partition_tm = te.ConnectionSplit(args.alg, args.group)
    end = datetime.now()
    # print elapsed time in microseconds
    print("Elapsed", (end - start).total_seconds(), "s")

    ordered_paths, result = te.solve(partition_tm)

    print("path:" + str(ordered_paths))
    print("Optimal:" + str(result))
# with open('../test/data/connection.json') as f:
#       connection= json.load(f)
#
# g = GetNetworkToplogy(25,0.4)
# print(Heuristic_CSP(connection,g))
