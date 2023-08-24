#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep  7 13:42:31 2022

@author: Yufeng Xin (RENCI)
"""

import copy
from dataclasses import dataclass
from itertools import chain, cycle
from typing import List, Tuple, Union

import networkx as nx
import numpy as np
from ortools.linear_solver import pywraplp

from sdx_pce.models import ConnectionPath, ConnectionSolution, TrafficMatrix
from sdx_pce.utils.constants import Constants
from sdx_pce.utils.functions import GraphFunction


@dataclass
class DataModel:
    constraint_coeffs: List[List]
    bounds: List
    num_constraints: int
    obj_coeffs: List
    num_vars: int
    num_inequality: int


class TESolver:
    """
    Traffic Engineering Solver.
    """

    def __init__(
        self,
        graph: nx.Graph,
        tm: TrafficMatrix,
        cost_flag=Constants.COST_FLAG_HOP,
        objective=Constants.OBJECTIVE_COST,
    ):
        """
        :param graph: A NetworkX graph that represents a network
            topology.
        :param tm: Traffic matrix, in the form of a list of connection
            requests.
        :param cost_flag: Cost (weight) to assign per link.
        :param objective: What to solve for: cost or load balancing.
        """
        assert isinstance(graph, nx.Graph)
        assert isinstance(tm, TrafficMatrix)

        self.graph = graph
        self.tm = tm

        self.graphFunction = GraphFunction()
        self.graphFunction.set_graph(self.graph)
        self.graphFunction.weight_assign(cost_flag)

        self.objective = objective

        self.links = []  # list of links[src][dest], 2*numEdges

    def solve(self) -> Tuple[Union[ConnectionSolution, None], float]:
        """
        Return the computed path and associated cost.
        """
        data = self._create_data_model()
        if data is None:
            print("Could not create a data model")
            return ConnectionSolution(connection_map=None, cost=0)

        # Create the mip solver with the SCIP backend.
        solver = pywraplp.Solver.CreateSolver("SCIP")

        x = {}
        for j in range(data.num_vars):
            x[j] = solver.IntVar(0, 1, "x[%i]" % j)

        print(f"Number of variables = {solver.NumVariables()}")
        print(f"num_constraints: {data.num_constraints}")
        print(f"num_inequality: {data.num_inequality}")

        for i in range(data.num_constraints - data.num_inequality):
            constraint_expr = [
                data.constraint_coeffs[i][j] * x[j] for j in range(data.num_vars)
            ]
            solver.Add(sum(constraint_expr) == data.bounds[i])

        print(len(data.bounds))
        # print(data.bounds)
        print(len(data.constraint_coeffs))
        # print(data.constraint_coeffs)
        print(data.num_inequality)

        for i in range(
            data.num_constraints - data.num_inequality, data.num_constraints
        ):
            constraint_expr = [
                data.constraint_coeffs[i][j] * x[j] for j in range(data.num_vars)
            ]
            solver.Add(sum(constraint_expr) <= data.bounds[i])

        print(f"Number of constraints = {solver.NumConstraints()}")

        objective = solver.Objective()
        for j in range(data.num_vars):
            objective.SetCoefficient(x[j], data.obj_coeffs[j])
        objective.SetMinimization()

        status = solver.Solve()
        solution = []
        paths = None
        if status == pywraplp.Solver.OPTIMAL:
            print(f"Objective value = {solver.Objective().Value()}")
            for j in range(data.num_vars):
                # print(x[j].name(), ' = ', x[j].solution_value())
                solution.append(x[j].solution_value())

            paths = np.array(solution).reshape(len(self.tm.connection_requests), -1)
            print(paths.shape)
            # print(path)

            # print('Problem solved in %f milliseconds' % solver.wall_time())
            # print('Problem solved in %d iterations' % solver.iterations())
            # print('Problem solved in %d branch-and-bound nodes' % solver.nodes())
        else:
            print("The problem does not have an optimal solution.")

        # returns: dict(conn request, [path]), cost
        return self._solution_translator(paths, solver.Objective().Value())

    def _solution_translator(
        self, paths: list, cost: float
    ) -> Union[ConnectionSolution, None]:
        # extract the edge/path
        real_paths = []
        if paths is None:
            print("No solution: empty input")
            return ConnectionSolution(connection_map=None, cost=cost)
        for path in paths:
            real_path = []
            i = 0
            for edge in path:
                if abs(edge - 1) < 0.001:  # =1: edge on the path
                    real_path.append(self.links[i])
                i = i + 1
            real_paths.append(real_path)

        # associate with the TM requests
        id_connection = 0

        result = ConnectionSolution(connection_map={}, cost=cost)

        for request in self.tm.connection_requests:
            src = request.source
            dest = request.destination
            # latency = connection[3]  # latency is unused

            # Add request as the key to solution map
            result.connection_map[request] = []

            # ordered_path: List[Path] = []
            # ordered_paths: List[(src, dest, bw)] = [] # ordered_path
            # ordered_paths: List = []
            # print("src:"+str(src)+"-dest:"+str(dest))
            path = real_paths[id_connection]
            i = 0
            while src != dest and i < 10:
                for edge in path:
                    # print("edge:"+str(edge))
                    if edge[0] == src:
                        print(f"Adding edge {edge} for request {request}")
                        # ordered_paths.append(edge)

                        # Make a path and add it to the solution map
                        cpath = ConnectionPath(source=edge[0], destination=edge[1])
                        result.connection_map[request].append(cpath)

                        src = edge[1]
                        break
                    # if src==dest:
                    #    print("ordered the path:"+str(src) +":"+str(dest)+":"+str(i)+";"+str(ordered_path))
                    #    break
                i = i + 1
            id_connection = id_connection + 1
        # print("ordered paths:"+str(ordered_paths))
        # return ordered_paths

        print(f"solution_translator result: {result}")
        return result

    def update_graph(self, graph, pathsconnection):
        """
        After a path is provisioned, it needs to update the topology by subtracting the used bandwidth
        """
        paths = pathsconnection.connection_map
        if paths is None:
            return graph
        for connection, path in paths.items():
            # src = connection[0]   # src is unused
            # dest = connection[1]  # dest is unused
            bw = connection.required_bandwidth

            for edge in path:
                u = edge.source
                v = edge.destination
                if graph.has_edge(u, v):
                    bandwidth = graph[u][v][Constants.BANDWIDTH] - bw
                    graph[u][v][Constants.BANDWIDTH] = max(
                        bandwidth, 0.01
                    )  # Avoid being divided by 0.
        return graph

    def set_obj(self, obj):
        self.objective = obj

    def _mc_cost(self, links):
        """
        Defining the link cost function to be a constant weight
        """
        cost_list = []
        for link in links:
            cost_list.append(self.graph[link[0]][link[1]][Constants.WEIGHT])

        cost = []
        for i in range(len(self.tm.connection_requests)):
            cost += cost_list

        return cost

    def _lb_cost(self, links):
        """
        Defining the link cost function to be the bw utilization
        """
        cost_list = []
        for link in links:
            cost_list.append(self.graph[link[0]][link[1]][Constants.BANDWIDTH])
        cost = []
        for connection in self.tm.connection_requests:
            bw = connection.required_bandwidth
            # cost += cost_list
            cost += [bw / link for link in cost_list]

        return cost

    def _create_data_model(self) -> DataModel:
        """
        Top function to create the OR optimization model in the array format
        """

        latency = True

        nodenum = self.graph.number_of_nodes()
        linknum = self.graph.number_of_edges()

        print(f"Creating data model: #nodes: {nodenum}, #links: {linknum}")

        # graph flow matrix
        inputmatrix, links = self._flow_matrix(self.graph)
        self.links = links
        # inputdistancelist:link weight
        # distance_list=self.graph_generator.get_distance_list()
        # latency_list=self.graph_generator.get_latency_list()

        # print("distance_list:"+str(np.shape(distance_list)))
        # print("latency_list:"+str(np.shape(latency_list)))

        latconstraint = self._make_latency_constaints(links)

        # form the bound: rhs
        # flows: numnode*len(request)
        bounds = []
        for request in self.tm.connection_requests:
            rhs = np.zeros(nodenum, dtype=int)

            # Avoid going past array bounds.
            if request.source > nodenum or request.destination > nodenum:
                print(
                    f"Cannot create data model: "
                    f"request.source ({request.source}) or "
                    f"request.destination ({request.destination}) "
                    f" > num nodes ({nodenum})"
                )
                return None

            rhs[request.source] = -1
            rhs[request.destination] = 1
            bounds += list(rhs)

        print(f"bound 1: {len(bounds)}")

        # rhsbw -TODO *2 edges
        bwlinklist = []
        for link in links:
            u = link[0]
            v = link[1]
            if self.graph.has_edge(u, v):
                bw = self.graph[u][v][Constants.BANDWIDTH]
            elif self.graph.has_edge(v, u):
                bw = self.graph[v][u][Constants.BANDWIDTH]

            bwlinklist.append(bw)

        # add the bwconstraint rhs
        bounds += bwlinklist
        print(f"bound 2: {len(bounds)}")

        # add the latconstraint rhs
        if latency:
            bounds += latconstraint["rhs"]
            print(f"bound 3: {len(bounds)}")
            # print(bounds)

        # form the constraints: lhs
        flowconstraints = self._lhsflow(self.tm.connection_requests, inputmatrix)
        bwconstraints = self._lhsbw(self.tm.connection_requests, inputmatrix)

        print(f"\nConstraints Shape:{len(flowconstraints)}:{len(bwconstraints)}")
        # print("\n flow"+str(flowconstraints))
        # print("\n bw:"+str(type(bwconstraints)))

        bw_np = np.array(bwconstraints)
        print(f"np:{flowconstraints.shape} : {bw_np.shape}")
        flow_lhs = np.concatenate((flowconstraints, bw_np))
        print(f"flow_lhs: {np.shape(flow_lhs)}")

        if latency:
            print(f"latcons: {np.shape(latconstraint['lhs'])}")
            lhs = np.concatenate((flow_lhs, latconstraint["lhs"]))
        else:
            lhs = flow_lhs

        # objective function
        if self.objective == Constants.OBJECTIVE_COST:
            print("Objecive: Cost")
            cost = self._mc_cost(links)
        if self.objective == Constants.OBJECTIVE_LOAD_BALANCING:
            print("Objecive: Load Balance")
            cost = self._lb_cost(links)

        print(f"cost len: {len(cost)}")
        # print(cost)
        print(f"lhs shape: {lhs.shape}")
        print(f"rhs shape: {len(bounds)}")

        coeffs = []
        for i in range(lhs.shape[0]):
            row = list(lhs[i])
            coeffs.append(row)

        # Form the OR datamodel
        return DataModel(
            constraint_coeffs=coeffs,
            bounds=list(bounds),
            num_constraints=len(bounds),
            obj_coeffs=list(cost),
            num_vars=len(cost),
            num_inequality=2 * linknum + int(len(self.tm.connection_requests)),
        )

    def _flow_matrix(self, g):
        """generating the network flow matrix
        # also set self.links: 2*links
        """
        nodenum = len(g.nodes)
        linknum = 2 * len(g.edges)

        # Adjcent matrix, key:node; value:list of neighboring nodes
        adj = nx.to_dict_of_lists(g)

        keys = adj.keys()
        links = []
        # list of all links

        for k in keys:
            links = chain(links, zip(cycle([k]), adj[k]))

        # list of links directional: tuple (src,nei), len =2*#edges
        link_list = list(links)
        # print(link_list)

        # flow matrix: 1 means flow into the nodes, -1 meanse flow out of the node
        inputmatrix = np.zeros((nodenum, linknum), dtype=int)
        n = 0
        for link in link_list:
            src = link[0]
            dest = link[1]
            # print(str(src)+":"+str(dest)+"\n")
            inputmatrix[src][n] = -1
            inputmatrix[dest][n] = 1
            n += 1

        return inputmatrix, link_list

    def _lhsflow(self, request_list, inputmatrix):
        """
        lefthand matrix of the network flow equation. shape: (len(tm)*numnode, len(num)*2*numedge)
        """
        r = len(request_list)
        m, n = inputmatrix.shape
        print(f"r={r}:m={m}:n={n}")
        # out = np.zeros((r,m,r,n), dtype=inputmatrix.dtype)
        # diag = np.einsum('ijik->ijk',out)
        # diag[:] = inputmatrix
        # print("diag:" + str(diag.shape))
        # return diag.reshape(m*r,n*r)
        # print(inputmatrix)
        out = np.zeros((r * m, r * n), dtype=inputmatrix.dtype)
        for i in range(r):
            out[i * m : (i + 1) * m, i * n : (i + 1) * n] = inputmatrix
        print(f"out: {out.shape}")
        return out

    def _lhsbw(self, request_list, inputmatrix):
        """
        Form bandwidth constraints.

        To learn what this means, see the formulation diagram at
        https://github.com/atlanticwave-sdx_pce/tree/main/Documentation.

        The yellow portion of the diagram is the "inputmatrix" input
        to this function.  The return value should represent the green
        portion, which is the bandwidth constraints computed here.
        """
        bwconstraints = []
        # zeros = self.zerolistmaker(len(inputmatrix[0])*len(request_list))
        zeros = np.zeros(len(inputmatrix[0]) * len(request_list), dtype=int)
        for i in range(len(inputmatrix[0])):
            addzeros = copy.deepcopy(zeros)
            bwconstraints.append(addzeros)
            count = 0

            for request in request_list:
                # print(
                #     f"bwconstraints: {bwconstraints}, request: {request}, request_list: {request_list}"
                # )
                # print(
                #     f"i: {i}, count: {count} len(inputmatrix[0]): {len(inputmatrix[0])}, inputmatrix: {inputmatrix}"
                # )
                # print(
                #     f"i + count * len(inputmatrix[0]: {i + count * len(inputmatrix[0])}"
                # )

                k = i + count * len(inputmatrix[0])
                bwconstraints[i][k] = request.required_bandwidth
                count += 1

        return bwconstraints

    def _make_latency_constaints(self, links):
        lhs = []
        rhs = []

        request_list = self.tm.connection_requests
        print(f"request: {len(request_list)}")
        print(f"links: {len(links)}")

        zerolist = np.zeros(len(links), dtype=int)
        latency_list = []
        for link in links:
            latency_list.append(self.graph[link[0]][link[1]][Constants.LATENCY])

        requestnum = len(request_list)
        for i in range(requestnum):
            constraint = []
            constraint = (
                i * zerolist.tolist()
                + latency_list
                + (requestnum - 1 - i) * zerolist.tolist()
            )
            # print("constraint:"+str(len(constraint)))
            lhs.append(constraint)

        for request in request_list:
            rhs.append(request.required_latency)

        latdata = {}
        latdata["lhs"] = lhs
        latdata["rhs"] = rhs

        return latdata

    def is_connected(self):
        return nx.is_connected(self.graph)

    def is_bi_connected(self):
        pass
