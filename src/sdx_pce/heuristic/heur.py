import argparse
import json

# importing the module
from datetime import datetime

import numpy as np
import prtpy

from sdx_pce.load_balancing.te_solver import TESolver
from sdx_pce.models import ConnectionRequest, TrafficMatrix
from sdx_pce.utils.constants import Constants
from sdx_pce.utils.random_connection_generator import RandomConnectionGenerator
from sdx_pce.utils.random_topology_generator import RandomTopologyGenerator

from sdx_pce.heuristic.csv_network_parser import *
from sdx_pce.heuristic.path_te_solver import *

from sdx_pce.utils.functions import bw_stat


l_lat=80
u_lat=100
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
        request = ConnectionRequest(
            source=rq[0],
            destination=rq[1],
            required_bandwidth=rq[2],
            required_latency=rq[3],
        )
        traffic_matrix.connection_requests.append(request)
    return traffic_matrix

def demand_to_connection(demands):
    """
    Convert the plain traffic matrix to TrafficMatrix model used by TESolver as input
    """
    traffic_matrix = TrafficMatrix(connection_requests=[])
    print(f"Number of Demands:{len(demands)}")
    for d, demand in demands.items():
        if demand.src==demand.dst:  continue 
        request = ConnectionRequest(
            source=int(demand.src)-1,
            destination=int(demand.dst)-1,
            required_bandwidth=demand.amount,
            required_latency = np.random.randint(l_lat, u_lat)
        )
        #print(request)
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
    scale=2
    if args.topology_file is not None:
        if args.te_file is not None:
            # graph, tm = dot_file(args.topology_file, args.te_file)
            network = parse_topology(args.topology_file)
            parse_demands(network, args.te_file, scale)
            print("Supporting dot file later!")
        else:
            print("Missing the TE file!")
            exit()
    else:
        p = 0.2
        n = 25

        graph, tm = random_graph(n, p, args.m)

    if args.alg >=10:
        parse_tunnels(network)
        initialize_weights(network)

        if args.alg ==10:    
            #Original tunnel-based  MS solver for flow maximization 
            mip = CvxSolver()
            solver = MSSolver(mip, network)
            solver.add_demand_constraints()
            solver.add_edge_capacity_constraints()
            solver.Maximize(get_max_flow_objective(network))

            result = solver.solve()
            ordered_paths=solver.mip.problem.status
            if mip.problem.status == 'optimal':
                print("Optimal solution was found.")
                print("Max flow:", result)   
                solution=get_edge_flow_allocations(network)
                print(solution)       
        
        if args.alg ==11:    
            #Original tunnel-based MS solver for FCC flow maximization 
            mip = CvxSolver()
            solver = FFCSolver(mip, network)

            solver.add_demand_constraints()
            solver.add_edge_capacity_constraints()

            # Enumerate single link failures (k = 1)
            for edge in network.edges:
                # edges are directional tuples, thus, failing (a,b) implies that (b,a) also fails.
                edges = set([network.edges[edge], network.edges[edge[::-1]]])
                solver.failure_scenario_edge_constraint(edges)

            objective = get_ffc_objective(network)
            solver.Maximize(objective)
            result = solver.solve()
            if mip.problem.status == 'optimal':
                print("Optimal solution was found.")
                print("Optimal objective:", result)
            else:
                print("Optimal solution was not found.")

        if args.alg ==20:
            # Tunnel-based flow maximization solver with OR Tools 
            # More statistics on link utilization, etc
            path_solver=PathTESolver(network)
            path_solver.create_data_model()
            path_solver.Maximize()
            ordered_paths, result = path_solver.solve()
            edge_flow=path_solver.get_edge_flow_allocations()
            print(edge_flow)
            demands_unmet=path_solver.get_demands_unmet()
            print(demands_unmet)

        if args.alg ==21:
            print("FCC with link failure resiliency")
            # Tunnel-based flow maximization FCC solver with OR Tools 
            # More statistics on link utilization, etc
            fcc_solver=FCCPathTESolver(network)
            fcc_solver.create_data_model()
            # Enumerate single link failures (k = 1)
            for edge in network.edges:
            # edges are directional tuples, thus, failing (a,b) implies that (b,a) also fails.
                edges = set([network.edges[edge], network.edges[edge[::-1]]])
                fcc_solver.failure_scenario_edge_constraint(edges)
            fcc_solver.Maximize_FCC()
            ordered_paths, result = fcc_solver.solve()
            edge_flow=fcc_solver.get_edge_flow_allocations()
            print(f"Edge flow:\n{edge_flow}")
            demands_met=fcc_solver.get_demands_met()
            print(f"Met Demands:{demands_met}")
            demands_unmet=fcc_solver.get_demands_unmet()
            print(f"Unmet Demands:{demands_unmet}")

        #network.update_bw(edge_flow)
        graph = network.update_graph_edge_flow()
    else:
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

    #print(f"path: {ordered_paths}")
    print(f"Optimal: {result}")
    util_dict = bw_stat(graph)
    print(f"link utility:\n{util_dict}")
