import random
import csv
import json
import networkx as nx

from sdx_pce.heuristic.network_topology import *

def parse_topology(network_name):
    network = Network(network_name)
    with open(network_name) as fi:
        reader = csv.reader(fi, delimiter=" ")
        for row_ in reader:
            if row_[0] == 'to_node': continue
            row = [x for x in row_ if x]
            to_node = row[0]
            from_node = row[1]
            capacity = int(float(row[2])/1000.0)
            network.add_node(to_node, None, None)
            network.add_node(from_node, None, None)
            network.add_edge(from_node, to_node, 200, capacity)      
    return network

def parse_demands(network, demand_file,scale=1):
    num_nodes = len(network.nodes)
    demand_matrix = {}
    with open(demand_file) as fi:
        reader = csv.reader(fi, delimiter=" ")
        for row_ in reader:
            if row_[0] == 'to_node': continue
            row = [float(x) for x in row_ if x]
            assert len(row) == num_nodes ** 2
            for idx, dem in enumerate(row):
                from_node = int(idx/num_nodes) + 1
                to_node = idx % num_nodes + 1
                assert str(from_node) in network.nodes
                assert str(to_node) in network.nodes
                if from_node not in demand_matrix:
                    demand_matrix[from_node] = {}
                if to_node not in demand_matrix[from_node]:
                    demand_matrix[from_node][to_node] = []
                demand_matrix[from_node][to_node].append(dem/1000.0)
        for from_node in demand_matrix:
            for to_node in demand_matrix[from_node]:
                max_demand = max(demand_matrix[from_node][to_node])
                network.add_demand(str(from_node), str(to_node), max_demand, scale)
    if network.tunnels:
        remove_demands_without_tunnels(network)
    return network.demands

def parse_tunnels(network, T=5, H_T=False):
    # Parse tunnels
    print(f"Parse Tunnels\n")
    N_T=T #heter num_tunnels
    for node1 in network.nodes:
        for node2 in network.nodes:
            if node1 == node2: continue
            if H_T == True:
                N_T=num_tunnnels(network,node1, node2,T)
            #print(f"{(node1,node2)}:{network.demands[(node1,node2)].amount}:{N_T}")
            paths = network.k_shortest_paths(node1, node2, N_T)
            for path in paths:
                tunnel = network.add_tunnel(path)
    if network.demands:
        remove_demands_without_tunnels(network)

# adjust the number of tunnels per demand according to demand distribution
def num_tunnnels(network,node1, node2,T):
    N_T=T
    delta_demand = (network.max_demand-network.min_demand)/(T-1)
    min_demand = network.min_demand - 0.5
    demand=network.demands[(node1,node2)].amount
    for i in range(T-1):
        if demand > min_demand + i*delta_demand and demand <= network.min_demand + (i+1)*delta_demand:
            N_T=i+2
            break
    return N_T

def remove_demands_without_tunnels(network):
    removable_demands = [p for p, d in network.demands.items() if not d.tunnels]
    for demand_pair in removable_demands:
        del network.demands[demand_pair]

def initialize_weights(network):
    for tunnel in network.tunnels.values():
        tunnel.add_weight(random.randint(1, 10))

def parse_topology_json(network_name):
    network = Network(network_name)
    with open(network_name) as fi:
        reader = json.load(fi)
    graph=nx.node_link_graph(reader)
    #node index starts from 0 -> +1
    for u,v,p in graph.edges(data=True):
        network.add_edge(str(u+1), str(v+1), 200, p['capacity']*500.0)  

    return network

def generate_demand_from_b4(b4_demand,network):
    pass    
