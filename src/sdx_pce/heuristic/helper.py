import networkx as nx
from scipy.stats import lognorm

#demand lognorm distribution fomr B4 demand TM
S=1.70641
LOC=0.0795022
SCALE=52.6563

def get_max_flow_objective(network):
    """sum of all flows in all tunnels
    """
    return sum([t.v_flow for t in network.tunnels.values()])

def get_max_flow_min_weight_objective(network, epsilon=0.01):
    """sum of all flows in all tunnels penalized for weight
    each tunnel flow is reward with 1 - tunnel weight*epsilon
    """
    def reward(tunnel):
        return (1 - epsilon * tunnel.weight) * tunnel.v_flow
    return sum([reward(t) for t in network.tunnels.values()])

def get_ffc_objective(network):
    return sum([demand.b_d for demand in network.demands.values()])

def get_wavelength_objective(network):
    objective = 0
    for shortcut in network.shortcuts.values():
        objective += (len(shortcut.path) -1 )* shortcut.w_s
    return objective

def get_edge_flow_allocations(network):
    """ 
    Get the optimal edge allocations.
    """
    flow_labels = {}
    for edge in network.edges.values():
        #print(f"edge_capacity:{edge.capacity}")
        allocation = 0
        for tunnel in edge.tunnels:
            allocation += tunnel.v_flow.value
        utility=allocation/edge.capacity
        flow_labels[edge.e] = (round(allocation[0], 2),utility)
    return flow_labels

def get_demands_met(network):
    demands_met = {}
    for demand in network.demands.values():
        #print(f"demand:{demand}\n")
        flow_on_tunnels = sum([tunnel.v_flow.value for tunnel in demand.tunnels])
        #for tunnel in demand.tunnels:
        #    print(f"tunnel_flow={tunnel.v_flow.value}")
        if demand.amount<=flow_on_tunnels[0]:
            demands_met[(demand.src, demand.dst)] = flow_on_tunnels[0]
    return demands_met

def get_demands_unmet(network):
    demands_unmet = {}
    total_demands=0.0
    total_flows=0.0
    for demand in network.demands.values():
        flow_on_tunnels = sum([tunnel.v_flow.value for tunnel in demand.tunnels])
        total_demands=total_demands+demand.amount
        total_flows=total_flows+flow_on_tunnels
        if demand.amount - flow_on_tunnels > 0.1:
            demands_unmet[(demand.src, demand.dst)] = (demand.amount,(demand.amount-flow_on_tunnels)/demand.amount)
    unmet_percentage=(total_demands-total_flows)/total_demands
    print(f"Total_demands:{total_demands};total_flows:{total_flows};Overprovisioning percentage:{unmet_percentage}")
    return demands_unmet

#return a DiGraph with updated bandwidth.
def update_graph_edge_flow(g):
    import networkx
    graph = networkx.DiGraph()
    for n in g.nodes.keys():
        graph.add_node(n)
        # update with bandwidth, available bandwidth
    for edge in g.edges.values():
        s=edge.e[0]
        t=edge.e[1]
        allocation = 0
        for tunnel in edge.tunnels:
            allocation += tunnel.v_flow.value
        edge.avail_capacity = max(0,edge.avail_capacity-allocation)
        graph.add_edge(s, t, original_bandwidth=edge.capacity, bandwidth=edge.avail_capacity, distance=400)
    return graph  

def criticality(network, flow_labels):
    """
    input:
        total demand: network.total_demand
        tunnel.path: list of edges
        solution: tunnel.v_flow.SolutionValue()
    function: 
        link criticality=
        network criticality R = sum s*f
    output: dict{link:criticality}, R
    """
    #link criticality
    criticality_list={}
    linknum = len(network.edges)
    num_tunnels=len(network.tunnels)
    used_tunnels=0
    for demand in network.demands.values():
        #print(f"demand:{demand}\n")
        b_f=0.
        u_max=0
        e_max=None
        for tunnel in demand.tunnels:
            if tunnel.v_flow.value > 0.:
                used_tunnels=used_tunnels+1
                b_f=b_f+tunnel.v_flow.value
            #print(f"Tunnel:{tunnel};b_f:{b_f};tunnel_flow:{tunnel.v_flow.value}")
            for e in tunnel.path:
                allocation, utility=flow_labels[e.e]
                if u_max < utility:
                    u_max=utility
                    e_max=e
                    #print(f"e_max:{e_max};e:{e}; utility:{utility}")
        criticality=b_f/network.total_demands
        #print(f"e_max:{e_max};criticality:{criticality}")
        if e_max in criticality_list:
            criticality_list[e_max]=+criticality
        else:
            criticality_list[e_max]=criticality

    network_criticality=0.
    for edge in network.edges.values():
        if edge in criticality_list:
            allocation, utility=flow_labels[edge.e]
            criticality=criticality_list[edge]
            network_criticality=network_criticality + criticality/utility
    print(f"used tunnels:{used_tunnels};{used_tunnels/num_tunnels}")
    print(f"criticality list:{len(criticality_list)};{len(criticality_list)/linknum}")
    return criticality_list, network_criticality

#Generate demand following the lognorm distribution fitted from the B4 TM data
def generate_demand(network,sca,s=S,loc=LOC,scale=SCALE):
    num_nodes=len(network.nodes.values())
    size=num_nodes*(num_nodes-1)
    r = lognorm.rvs(s,loc,scale,size)
    i=0
    print(f"num_node={num_nodes};demand_size={size}")
    for from_node in network.nodes.values():
        for to_node in network.nodes.values():
            if from_node is not to_node:
                network.add_demand(str(from_node.mkt), str(to_node.mkt), r[i], sca)
                i=i+1
    return network.demands

def shortest_path_by_distance(G, v1, v2, nhops):
    sp_list = nx.all_shortest_paths(G, v1, v2)
    shortest_path_to_distance = {}
    for sp in sp_list:
        if len(sp) > nhops: continue
        sp_str = ':'.join(sp)
        sp_distance = 0
        for node1, node2 in zip(sp, sp[1:]):
            sp_distance += G[node1][node2]["distance"]

        assert sp_distance > 0
        shortest_path_to_distance[sp_str] = sp_distance
        
    if not shortest_path_to_distance: return None, None
    sorted_sps = sorted(shortest_path_to_distance.items(), key=lambda x:x[1])
    return sorted_sps[0][0], sorted_sps[0][1]

def unity_from_distance(shortcut_distance):
    if shortcut_distance <= 800:
        unity = 200
    elif shortcut_distance <= 2500:
        unity = 150
    elif shortcut_distance <= 5000:
        unity = 100
    else:
        unity = 0
    return unity

def get_viable_failures(network, k=1):
    """
    Returns the set of edge tuples that can fail.
    """
    return []

