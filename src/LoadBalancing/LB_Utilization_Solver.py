
# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  7 13:42:31 2022

@author: yifeiwang, Yufeng Xin at RENCI
"""

from ortools.linear_solver import pywraplp
import json


def create_data_model(graph):
    with open('./tests/data/connection.json') as f:
          query_list = json.load(f)
    commodity_query_list = []
    for query in query_list:
        commodity_query_list.append(query[2])
    with open('./tests/data/bwlinklist.json') as f:
          bwlist = json.load(f)
    obj_coeffs = []
    for bw in commodity_query_list:
        obj_coeffs+=[bw/link for link in bwlist]




    data = {}
    data['constraint_coeffs'] = graph['constraint_coeffs']


    data['bounds'] = graph['bounds']
    # data['bounds'].append(int(max_latency)) # append the user input min_latency to the RHS of the last constraint



    # data['obj_coeffs'] = graph['obj_coeffs']
    data['obj_coeffs'] = obj_coeffs

    data['num_vars'] = graph["num_vars"]
    data['num_constraints'] = graph['num_constraints']

    num_inequality = graph['num_inequality']




    return (data, num_inequality)

def split(list_a, chunk_size):
    for i in range(0, len(list_a), chunk_size):
        yield list_a[i:i + chunk_size]


def pathlookup(solution, linknum ,linklist):
    with open(linklist) as f:
        linklist = json.load(f)

    linkindex = []
    for i in range(len(solution)):
        if abs(solution[int(i)] - 1) < 0.01:
            linkindex.append(i)
    linkselection = []

    for i in linkindex:
        linkselection.append(linklist[int(i)])
    return (linkselection ,linkindex)

def solutiontranslator(solution):
    output = []
    c = 0
    for i in solution:
        if abs(i - 1) <= 0.001:
            output.append(c)
            c+=1
    return output


def solution_translator(solution, linklistname):
    with open(linklistname) as f:
        linklist = json.load(f)
    link_num = len(linklist)

    solution_list = list(split(solution, link_num))
    path_list = {}
    c = 1
    for request in solution_list:
        individual_solution = []
        i = 0

        for solution in request:
            if abs(solution - 1) < 0.01:

                individual_solution.append(linklist[i])
            i += 1

        path_list[str(c)] = individual_solution
        c += 1
    ordered_path_list = pathordering(path_list)
    return ordered_path_list


def pathordering(path_list):
    ordered_path_list = {}
    source_list = []
    c = 0
    with open('./tests/data/connection.json') as f:
        query_list = json.load(f)
    for query in query_list:
        source_list.append(query[0])

    for query in path_list:
        source_node = source_list[c]
        ordered_path_list[query] = []
        while len(path_list[query]) != 0:
            for path in path_list[query]:
                if path[0] == source_node:
                    ordered_path_list[query].append(path)
                    source_node = path[1]
                    path_list[query].remove(path)
        c += 1
    return ordered_path_list



def LB_Solver(data):
    graph = create_data_model(data)
    data = graph[0]
    num_inequality = graph[1]
    # Create the mip solver with the SCIP backend.
    solver = pywraplp.Solver.CreateSolver('SCIP')


    x = {}
    for j in range(data['num_vars']):
        x[j] = solver.IntVar(0, 1, 'x[%i]' % j)
    print('Number of variables =', solver.NumVariables())


    for i in range(data['num_constraints']-num_inequality):
        constraint_expr = [data['constraint_coeffs'][i][j] * x[j] for j in range(data['num_vars'])]
        solver.Add(sum(constraint_expr) == data['bounds'][i])
    for i in range(data['num_constraints']-num_inequality, data['num_constraints']):
        constraint_expr = [data['constraint_coeffs'][i][j] * x[j] for j in range(data['num_vars'])]
        solver.Add(sum(constraint_expr) <= data['bounds'][i])
    print('Number of constraints =', solver.NumConstraints())

    objective = solver.Objective()
    for j in range(data['num_vars']):
        objective.SetCoefficient(x[j], data['obj_coeffs'][j])
    objective.SetMinimization()

    status = solver.Solve()
    solution = []

    if status == pywraplp.Solver.OPTIMAL:
        print('Objective value =', solver.Objective().Value())
        for j in range(data['num_vars']):
            # print(x[j].name(), ' = ', x[j].solution_value())
            solution.append(x[j].solution_value())
        print()
        # print('Problem solved in %f milliseconds' % solver.wall_time())
        # print('Problem solved in %d iterations' % solver.iterations())
        # print('Problem solved in %d branch-and-bound nodes' % solver.nodes())
    else:
        print('The problem does not have an optimal solution.')

    return solution, solver.Objective().Value()

def runLB_UT_Solver():
    with open('./tests/data/LB_data.json') as f:
        data = json.load(f)

    output = LB_Solver(data)
    solution = output[0]
    objective =output[1]


    return [solution_translator(solution, './tests/data/LB_linklist.json'), objective]

# print(runLB_UT_Solver())
# sol = ({1: [[1, 11]], 2: [[3, 21], [21, 18]], 3: [[2, 13]]}, 0.06924572972593251)