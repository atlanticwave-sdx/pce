import argparse

import numpy as np

from Heuristic.Heur import TE_Group_Solver
from LoadBalancing.TE_Solver import TE_Solver
from Utility import global_name
from Utility.randomConnectionGenerator import RandomConnectionGenerator
from Utility.randomTopologyGenerator import RandomTopologyGenerator


def random_graph(n, p, m):

    graph_generator = RandomTopologyGenerator(n, p)
    graph = graph_generator.generate_graph()

    tm_generator = RandomConnectionGenerator(n)
    tm = tm_generator.randomConnectionGenerator(m, 500, 1000, 80, 100)

    return graph, tm


def dot_file(g_file, tm_file):
    pass


def bw_stat(g):
    total_weight = 0.0
    total_util = 0.0
    max_util = 0.0
    util_list = []
    for (u, v, w) in g.edges(data=True):
        avail_bw = w[global_name.bandwidth]
        bw = w[global_name.original_bandwidth]
        weight = global_name.alpha * (1.0 / (avail_bw + 0.1))
        total_weight = total_weight + weight
        util = 1.0 - avail_bw / bw
        total_util = total_util + util
        if util > max_util:
            max_util = util
        util_list.append(util)
    util_array = np.array(util_list)
    mean_util = np.mean(util_array)
    std_util = np.std(util_array)
    ninetypercetile_util = np.percentile(util_array, 90)
    # print(util_array)
    print(
        f"mean_util={mean_util};std_util={std_util};"
        f"ninetypercetile_util={ninetypercetile_util}"
    )
    print(
        f"total_weight={total_weight};total_util={total_util};" f"max_util={max_util}"
    )


if __name__ == "__main__":
    parse = argparse.ArgumentParser()

    parse.add_argument(
        "-n",
        dest="n",
        required=False,
        help="Number of nodes when creating random topology",
        type=int,
    )
    parse.add_argument(
        "-p",
        dest="p",
        required=False,
        help="Probability of links when random topology",
        type=float,
    )
    parse.add_argument(
        "-m",
        dest="m",
        required=False,
        help="Number of connections in the random TE",
        type=int,
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
        "-l", dest="l", required=False, help="Static link cost input", type=str
    )
    parse.add_argument(
        "-t",
        dest="te_file",
        required=False,
        help="Input file for the connections or traiffc matrix, e.g. c connection.json. Required.",
        type=str,
    )
    parse.add_argument(
        "-g",
        dest="topology_file",
        required=False,
        help="Input file for the network topology, e.g. t topology.json. Required.",
        type=str,
    )
    parse.add_argument(
        "-heur",
        dest="heur",
        default=0,
        help="Heuristic = 1, Default = 0 for the optimal. ",
        type=int,
    )
    parse.add_argument(
        "-k", dest="k", default=2, help="Group Heuristic  -- Number of groups", type=int
    )
    parse.add_argument(
        "-a",
        dest="alg",
        default=0,
        help="Flag for different grouping heuristic algorithms, default is the linear partition",
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

    if args.topology_file is not None:
        if args.te_file is not None:
            graph, tm = dot_file(args.topology_file, args.te_file)
        else:
            print("Missing the TE file!")
            exit()
    else:
        if args.n is None:
            args.n = 25
        if args.p is None:
            args.p = 0.2
        if args.m is None:
            args.m = 3
        print("n=" + str(args.n) + ";p=" + str(args.p) + ";m=" + str(args.m))
        graph, tm = random_graph(args.n, args.p, args.m)

    if args.c == global_name.COST_FLAG_STATIC:  # 4
        if args.l is None:
            print("Error: Static cost file is needed!")
            exit(1)

    if args.heur == 0:
        print("Optimal solver")
        solver = TE_Solver(graph, tm, args.c, args.b)
        path, result = solver.solve()
        ordered_paths = solver.solution_translator(path, result)
        graph = solver.update_graph(graph, ordered_paths)
    else:
        print("Heuristic solver")
        solver = TE_Group_Solver(graph, tm, args.c, args.b)
        partition_tm = solver.ConnectionSplit(args.alg, args.k)
        solver.solve(partition_tm)

    bw_stat(graph)
