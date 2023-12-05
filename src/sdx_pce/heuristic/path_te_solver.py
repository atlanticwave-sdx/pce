import copy
from dataclasses import dataclass
from itertools import chain, cycle
from typing import List, Mapping, Tuple, Union

import argparse
import csv
import networkx as nx
import numpy as np
from ortools.linear_solver import pywraplp

from sdx_pce.heuristic.network_topology import *
from sdx_pce.heuristic.csv_network_parser import *
from sdx_pce.heuristic.MIPSolver import GORSolver

from sdx_pce.load_balancing.te_solver import TESolver, DataModel

class PathTESolver:
    """
    Path Based Traffic Engineering Solver.
    """

    def __init__(    
        self,
        network:Network,
    ):
        """
        :param graph: A NetworkX graph that represents a network
            topology.
        :param tm: Traffic matrix, in the form of a list of connection
            requests.
        :param cost_flag: Cost (weight) to assign per link.
        :param objective: What to solve for: cost or load balancing.
        """
        self.network=network
        #random weight of tunnels
        initialize_weights(network)
        # Create the mip solver with the SCIP backend.
        self.solver = GORSolver()
        self.initialize_tunnel_variables()

    def create_data_model(self, latency=True) -> DataModel:
        """
        Top function to create the OR optimization model in the array format
        """
        nodenum = len(self.network.nodes)
        linknum = len(self.network.edges)


        edges=self.network.edges.values()
        print(f"Creating data model: #nodes: {nodenum}, #links: {linknum}")

        self._add_demand_constraints()
        self._add_edge_capacity_constraints()

    
    def _add_demand_constraints(self):
        """lhs: [L, D], rhs: [D]"""

        tunnels=self.network.tunnels.values()
        demands=self.network.demands.values()
        tunnelnum = len(tunnels)
        demandnum = len(demands)
        print(f"#tunnels: {tunnelnum}, #demands: {demandnum}")

        for demand in demands:
            assert len(demand.tunnels) > 0
            constraint = self.solver.solver.RowConstraint(0, demand.amount, "")
            for tunnel in demand.tunnels:
                constraint.SetCoefficient(tunnel.v_flow, 1.0)
            #print(f"Constraint:{str(constraint)}")

    def _add_edge_capacity_constraints(self):
        """lhs: [L, E], rhs: [E]"""
        for edge_pair in self.network.edges:
            edge = self.network.edges[edge_pair]
            constraint = self.solver.solver.RowConstraint(0, edge.capacity, "")
            #print(f"edge_capacity:{edge.capacity}")
            for tunnel in edge.tunnels:
                constraint.SetCoefficient(tunnel.v_flow, 1.0)
        print(f"Edge Constraints:{len(self.solver.solver.constraints())}")
                    
    def initialize_tunnel_variables(self):
        for tunnel in self.network.tunnels.values():
            tunnel.init_flow_var(self.solver)

    def Maximize(self):
        objective = self.solver.solver.Objective()
        for tunnel in self.network.tunnels.values():
            objective.SetCoefficient(tunnel.v_flow, 1)
        objective.SetMaximization()
        self.solver.Maximize(objective)

    def Maximize_FCC(self):
        objective = self.solver.solver.Objective()
        for demand in self.network.demands.values():
            objective.SetCoefficient(demand.b_d, 1)
        objective.SetMaximization()
        self.solver.Maximize(objective)

    def solve(self):
        print("Path TE Solver!")
        print(f"NumVariables:{len( self.solver.solver.variables())}")
        print(f"NumConstraints:{len( self.solver.solver.constraints())}")
        status = self.solver.Solve()
        result=-1.0
        ordered_paths = {} 
        if status == pywraplp.Solver.OPTIMAL:
            result=self.solver.solver.Objective().Value()
            ordered_paths=self.get_demand_flow_allocation()
            edge_load=self.get_edge_flow_allocations()

        else:
            print("The problem does not have an optimal solution.")

        return ordered_paths, result

    def get_demand_flow_allocation(self):
        ordered_paths={}
        for demand in self.network.demands.values():
            src=demand.src
            dst=demand.dst
            ordered_paths[(src,dst)]=demand.tunnels

        return ordered_paths

    def criticality(self, flow_labels):
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
        linknum = len(self.network.edges)
        num_tunnels=len(self.network.tunnels)
        used_tunnels=0
        for demand in self.network.demands.values():
            #print(f"demand:{demand}\n")
            b_f=0.
            u_max=0
            e_max=None
            for tunnel in demand.tunnels:
                if tunnel.v_flow.SolutionValue() > 0.:
                    used_tunnels=used_tunnels+1
                    b_f=b_f+tunnel.v_flow.SolutionValue()

                #print(f"Tunnel:{tunnel};b_f:{b_f};tunnel_flow:{tunnel.v_flow.SolutionValue()}")
                for e in tunnel.path:
                    allocation, utility=flow_labels[e]
                    if u_max < utility:
                        u_max=utility
                        e_max=e
                    #print(f"e_max:{e_max};e:{e}; utility:{utility}")
            criticality=b_f/self.network.total_demands
            #print(f"e_max:{e_max};criticality:{criticality}")
            if e_max in criticality_list:
                criticality_list[e_max]=+criticality
            else:
                criticality_list[e_max]=criticality

        network_criticality=0.
        for edge in self.network.edges.values():
            if edge in criticality_list:
                allocation, utility=flow_labels[edge]
                criticality=criticality_list[edge]
                network_criticality=network_criticality + criticality/utility
        print(f"used tunnels:{used_tunnels};{used_tunnels/num_tunnels}")
        print(f"criticality list:{len(criticality_list)};{len(criticality_list)/linknum}")
        return criticality_list, network_criticality

    def get_edge_flow_allocations(self):
        """ 
        Get the optimal edge allocations.
        """
        flow_labels = {}
        for edge in self.network.edges.values():
            allocation = 0
            for tunnel in edge.tunnels:
                allocation += tunnel.v_flow.SolutionValue()
            utility=allocation/edge.capacity
            flow_labels[edge] = (round(allocation, 2), utility)

        return flow_labels

    def get_demands_met(self):
        demands_met = {}
        for demand in self.network.demands.values():
            #print(f"demand:{demand}")
            flow_on_tunnels = sum([tunnel.v_flow.SolutionValue() for tunnel in demand.tunnels])
            #for tunnel in demand.tunnels:
            #    print(f"tunnel_flow={tunnel.v_flow.SolutionValue()}")
            demands_met[(demand.src, demand.dst)] = flow_on_tunnels
        return demands_met

    def get_demands_unmet(self):
        demands_unmet = {}
        total_demands=0.0
        total_flows=0.0
        for demand in self.network.demands.values():
            flow_on_tunnels = sum([tunnel.v_flow.SolutionValue() for tunnel in demand.tunnels])
            total_demands=total_demands+demand.amount
            total_flows=total_flows+flow_on_tunnels
            if demand.amount - flow_on_tunnels > 0.1:
                #demands_unmet[(demand.src, demand.dst)] = round(demand.amount - flow_on_tunnels)
                demands_unmet[(demand.src, demand.dst)] = (demand.amount,(demand.amount-flow_on_tunnels)/demand.amount)
        unmet_percentage=(total_flows-total_demands)/total_demands
        print(f"Total_demands:{total_demands};total_flows:{total_flows};Overprovisioning percentage:{unmet_percentage}")
        demands_stat={}
        demands_stat["total_demands"]=total_demands
        demands_stat["total_flows"]=total_flows
        demands_stat["overprovisioning"]=unmet_percentage
        demands_stat["num_unmet"]=len(demands_unmet)
        return demands_stat


class FCCPathTESolver(PathTESolver):
    """
    Path Based Traffic Engineering Solver with FCC resiliency
    """
    def __init__(    
        self,
        network:Network,
    ):
        PathTESolver.__init__(self, network)
            
        for demand in self.network.demands.values():
            demand.init_b_d(self.solver)

    
    def create_data_model(self, latency=True) -> DataModel:
        """
        Top function to create the OR optimization model in the array format
        """
        nodenum = len(self.network.nodes)
        linknum = len(self.network.edges)

        edges=self.network.edges.values()
        print(f"Creating data model: #nodes: {nodenum}, #links: {linknum}")

        print(f"NumVariables:{len(self.solver.solver.variables())}")
        self._add_demand_constraints()
        self._add_edge_capacity_constraints()
        
    def failure_scenario_edge_constraint(self, alpha):

        def tunnel_alpha(tunnel):
            return 0 if any(set(alpha) & set(tunnel.path)) else 1

        for demand in self.network.demands.values():
            #constraint = self.solver.solver.RowConstraint(0, demand.amount, "{alpha}")
            #constraint.SetCoefficient(demand.b_d, 1.0)
            c=[]
            for tunnel in demand.tunnels:
                #constraint.SetCoefficient(tunnel.v_flow, -1.0*tunnel_alpha(tunnel))
                c.append(tunnel.v_flow*tunnel_alpha(tunnel))
            self.solver.solver.Add(demand.b_d <= sum(c))
            
                            
    def _add_demand_constraints(self):
        """lhs: [L, D], rhs: [D]"""

        tunnels=self.network.tunnels.values()
        demands=self.network.demands.values()
        tunnelnum = len(tunnels)
        demandnum = len(demands)
        print(f"#tunnels: {tunnelnum}, #demands: {demandnum}")

        for demand in demands:
            constraint = self.solver.solver.RowConstraint(0, demand.amount, "")
            constraint.SetCoefficient(demand.b_d, 1.0)

        print(f"Demand Constraints:{len(self.solver.solver.constraints())}")
            
    def pairwise_failures(self):
        return itertools.combinations(self.network.edges.values(), r = 2)

class CRIPathTESolver(PathTESolver):
    """
    Path Based Traffic Engineering Solver with FCC Criticality
    """