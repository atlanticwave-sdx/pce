# Background

## Google OR-Tools

Solver in this OR-Tools is used to solve for the optimal solution. It
takes in the formulation matrix with defined objective functions and
relationships with RHS.

In this project, links are set to be binary variables which means if a
link is selected, the corresponding variable is 1, if a link is not
selected, the variable is 0.


## Constrained Shortest Path (CSP)

Randomgraph is used to generate the topology of a network. Each link
in the network will have three attributes: cost, latency and
bandwidth.

Topology will be generated in .json file. Other link info files will
aslo be generated for later use.

- nodes: Number of nodes in the graph
- p: Probability of link creation
- max_latency: Used for testing the heuristic sorting method. Can be
  set to 99999 for regular topology.
- bwlimit: Remove any link that is lower than this bwlimit. There is
  connectivity check before the final creation of the topology, new
  topology will be created if the current one is not connected.

Formualtion:

![CSP Formulation](./csp_formulation.png)

## Load Balancing

Load Balancing is developed based on the CSP problem. User can input a
list of queries and get the overall optimal solutions.

Example Formualtion:

![Load Balancing](./load_balancing.png)

## Utility and Benchmark

Other utility funcions are aslo included, such as: Dijkstra
algorithms, Network connectivity check, etc.

Benchmark results are also provided. Computation time and cost
difference std are being tested between solver formulation and
heurtistic sorting methods( by latency and by cost).
