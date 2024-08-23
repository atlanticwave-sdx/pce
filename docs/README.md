# Background

## Traffic Engineering
Traditional network protocols such as IP-TE and MPLS-TE rely on the constrained shortest path (CSP) algorithms to solve traffic engineering (TE) problem for connection requests under QoS and link capacity constraints. CSP optimization problem itself is NP-complete and leads the development of several heuristics based on shortest path or k-shortest path algorithms.

The logically centralized controller and separation of control plane and forwarding plane in SDN make the global TE optimization possible for an entire traffic matrix, instead of routing inidividual request sequentially. Majority TE systems focus on the layer-3 networks with a goal to maximize the splittable traffic flows under the link capacity and TM constraints. For commercial WAN ISP and the research and educational (R&E) networks, provisioning on-demand QoS-guaranteed layer-2 services is the most important service. Unfortunately this would add the integer constraints on the unsplittable flows, which leads to an even harder integer linear programming (ILP) problem formulation. 

PCE solves the optimal traffic engineering problem with a node-arc based integer linear programming (ILP) model with flexible objective function definitions (for example, load balancing). It uses the popular [Google OR-Tools][or-tools] solver to find the optimal solution of the ILP problem [ictc].     

In this model, a network is modeled as a bi-directional graph G(V, E) with a set of nodes V connected by a set of links E. Each link e(u, v) ∈ E, with its start node u and end node v, has a set of properties such as the maximum available band- width capacity We and the minimum transportation latency Le. It may also carry a cost function c_e. The traffic demands are defined as a set of commodities D. Each d(s,t) ∈ D is defined as a demand between a source node s ∈ V and a destination node t ∈ V with bandwidth requirement w_d and a latency constraint l_d. Together these demands are represented in a traffic matrix (TM). A demand d(s, t) is routed over a path from the node s to the node t in the network where a binary variable x_(e,d) is defined to represent if the edge e is on the path d in the TE solution.

Here's an example of how the ILP model is defined to route three connection requests (commodities) in a 5-node capacited network. 

<!-- TODO: expand discussion on this image -->

![Load Balancing](./load_balancing.png)

## VLAN Assignment
VLAN assignment is a requirement for layer-2 service after the paths are obtained from the TE solution.

PCE includes the function to pick the available VLAN and assign to the paths.

## Multi-domain topology

If the underneath topology is a multi-domain network consisting of more than one domains, PCE also includes computes a Breakdown for each path: a list of path segments on the boundary points of each domain on the path.     

# Input and output

A topology will be represented in a JSON format. Each link in the
network could have three optional attributes: cost, latency and bandwidth.

A traffic matrix is defined in a JSON format to represent a set of connection requests.

The output is in a JSON format that represents the computed path segments with assigned VLANs.

# Utility and Benchmark

<!-- TODO: is this up-to-date? -->

Other utility funcions are aslo included, such as: reading topology files in other formats (dot and csv), shortest algorithms, network connectivity check, etc. A set of heuristics are also developed and implemented that achieve different performance and computation time tradeoffs.

There are scripts for the performance benchmark study conducted in a Slurm cluster.

Some benchmark results are also provided. 

<!-- URLs -->

[or-tools]: https://developers.google.com/optimization/
[ictc]: Y. Xin and Y. Wang, "Partitioning Traffic Engineering in Software Defined Wide Area Networks", ICTC'23.
