# PCE
## Run with python
### Functions
Most of the completed functions are located in the /LoadBalancing. It can solver CSP and Multi-commodities problem.

Multi_Input_LoadBalancer is used to generated topology of the network.

Multi_Input_Solver will generate the optimal solution based on minimizing the total cost.

LB_Utilization_Solver will generate the optimal solution based on minimizing the total link capacity utilization.

Connection.json is used as the query list and  located in the /test/data.
### Environment Setup

The network topology is generated by NetworkX and the traffic matrix computation is executed by Google OrTools Solver. 
```
pip3 install -r requirements.txt
```
Also, every data file was stored in test/data as json file. Remember to change the path according to local directory.

# Background
## Google OR-Tools
Solver in this OR-Tools is used to solve for the optimal solution. It takes in the formulation matrix with defined objective functions and relationships with RHS. 

In this project, links are set to be binary variables which means if a link is selected, the corresponding variable is 1, if a link is not selected, the variable is 0.

The objective function will be the sum of cost of all selected links.


## Constrained Shortest Path (CSP)

Randomgraph is used to generate the topology of a network. Each link in the network will have three attributes: cost, latency and bandwidth.

Topology will be generated in .json file. Other link info files will aslo be generated for later use.

- nodes: Number of nodes in the graph
- p: Probability of link creation
- max_latency: Used for testing the heuristic sorting method. Can be set to 99999 for regular topology.
- bwlimit: Remove any link that is lower than this bwlimit. There is connectivity check before the final creation of the topology, new topology will be created if the current one is not connected.

Formualtion:

![alt text](https://github.com/yifei666/pce/blob/e65eec6f1b4886e68c26d332420f64d34ff397eb/Reference/CSP_formulation_latex.png)

## Load Balancing

Load Balancing is developed based on the CSP problem. User can input a list of queries and get the overall optimal solutions. 

Example Formualtion:

![alt text](https://github.com/yifei666/pce/blob/91f8fb82f85d5ada8714b597c5cd5ae4979ba92b/Reference/LoadBalancing_Ex.png)

## Utility and Benchmark

Other utility funcions are aslo included, such as: Dijkstra algorithms, Network connectivity check, etc.

Benchmark results are also provided. Computation time and cost difference std are being tested between solver formulation and heurtistic sorting methods( by latency and by cost).
