import argparse

import Utility.global_name as global_name
from Utility.randomTopologyGenerator import RandomTopologyGenerator
from Utility.randomConnectionGenerator import RandomConnectionGenerator

from LoadBalancing.TE_Solver import TE_Solver
from Heuristic.Heur import TE_Group_Solver

def random_graph(n, p, m):
 
    graph_generator = RandomTopologyGenerator(n, p)
    graph=graph_generator.generate_graph()

    tm_generator = RandomConnectionGenerator(n)
    tm = tm_generator.randomConnectionGenerator(m, 500, 5000, 80, 100)

    return graph,tm

def dot_file(g_file, tm_file):
    pass

if __name__ == "__main__":
    parse = argparse.ArgumentParser()

    parse.add_argument('-n', dest='n', required=False, help='Number of nodes when creating random topology', type=int)
    parse.add_argument('-p', dest='p', required=False, help='Probability of links when random topology', type=float)
    parse.add_argument('-m', dest='m', required=False, help='Number of connections in the random TE', type=int)
    parse.add_argument('-c', dest='c', required=False, default=0, help='Link cost definition', type=int)
    parse.add_argument('-b', dest='b', required=False, default=0, help='Objective: MinCost or Load balancing', type=int)
    parse.add_argument('-l', dest='l', required=False, help='Static link cost input', type=str)
    parse.add_argument('-t', dest='te_file', required=False, help='Input file for the connections or traiffc matrix, e.g. c connection.json. Required.', type=str)
    parse.add_argument('-g', dest='topology_file', required=False, help='Input file for the network topology, e.g. t topology.json. Required.', type=str)
    parse.add_argument('-heur', dest='heur', default=0, help='Heuristic = 1, Default = 0 for the optimal. ', type=int)
    parse.add_argument('-o' , dest='result', default='OUTPUT.txt', help='Output file, e.g. o result.txt. If this option is not given, assume standard output.', type=str)

    parse.print_help()
    args = parse.parse_args()
    
    if args.topology_file is not None:
        if args.te_file is not None:
            graph, tm = dot_file(args.topology_file,args.te_file)
        else:
            print("Missing the TE file!")
            exit()    
    else:
        if args.n is None:
            print("Using default:"+"n=25;")
            args.n = 25
        if args.p is None:
            print("Using default:"+"p=0.2")
            args.p = 0.2
        if args.m is None:
            print("Using default:"+"m=3")
            args.m = 3

        graph, tm = random_graph(args.n,args.p,args.m)

    if args.c == global_name.COST_FLAG_STATIC: #4
        if args.l is None:
            print("Error: Static cost file is needed!")
            exit(1)

    if args.heur == 0:
        print(tm)
        solver = TE_Solver(graph, tm, args.c, args.b)
    else:
        solver = TE_Group_Solver(graph, tm, args.c, args.b)

    path,result = solver.solve()
