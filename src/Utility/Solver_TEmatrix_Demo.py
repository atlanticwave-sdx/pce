#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  1 15:16:36 2022

@author: yifeiwang
"""
import copy

constraint_matrix = []
commodity_matrix_1 = [1,1,0,0,0,0,0]
commodity_matrix_2 = [-1,0,1,1,0,0,0]
commodity_matrix_3 = [0,-1,-1,0,1,1,0]
commodity_matrix_4 = [0,0,0,-1,-1,0,1]
commodity_matrix_5 = [0,0,0,0,0,-1,-1]
zeros = [0,0,0,0,0,0,0]

commodity_matrix = []
commodity_matrix.append(commodity_matrix_1)
commodity_matrix.append(commodity_matrix_2)
commodity_matrix.append(commodity_matrix_3)
commodity_matrix.append(commodity_matrix_4)
commodity_matrix.append(commodity_matrix_5)




for line in commodity_matrix:
    constraint_matrix.append(line + zeros + zeros)


for line in commodity_matrix:
    constraint_matrix.append(zeros + line + zeros)
    
for line in commodity_matrix:
    constraint_matrix.append(zeros+ zeros+ line)
  

matrix_lessthan = []
threezeros = zeros*3

for i in range(7):
    zerosthree = copy.deepcopy(threezeros)
    matrix_lessthan.append(zerosthree)
    matrix_lessthan[i][i] = 15
    matrix_lessthan[-1][i+7] = 5
    matrix_lessthan[-1][i+14] = 10
    


    
    
    

bounds_equal = [1,0,0,-1,0,1,0,0,0,-1,0,1,0,0,-1]
bounds_lessthan = [20,10,10,20,40,10,30]
bounds = bounds_equal+bounds_lessthan
cost = [1,1,2,4,8,5,3,1,1,2,4,8,5,3,1,1,2,4,8,5,3]

finalmatrix = constraint_matrix + matrix_lessthan

print(len(bounds)-len(finalmatrix))
    




#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  7 13:42:31 2022

@author: yifeiwang
"""

from ortools.linear_solver import pywraplp
import json

def create_data_model():
    """Stores the data for the problem."""
    data = {}
    data['constraint_coeffs'] = finalmatrix
    data['bounds'] = bounds
    data['obj_coeffs'] = cost
    data['num_vars'] = len(finalmatrix[0])
    data['num_constraints'] = len(finalmatrix)
    for i in range(data['num_constraints']-7):
      # constraint_expr = [data['constraint_coeffs'][i][j] * x[j] for j in range(data['num_vars'])]
      print(data['constraint_coeffs'][i])
    print()

    return data




def main():
    data = create_data_model()
    # Create the mip solver with the SCIP backend.
    solver = pywraplp.Solver.CreateSolver('SCIP')


    x = {}
    for j in range(data['num_vars']):
        x[j] = solver.IntVar(0, 1, 'x[%i]' % j)
    print('Number of variables =', solver.NumVariables())

    # for i in range(data['num_constraints']):
    #     constraint = solver.RowConstraint(0, data['bounds'][i], '')
    #     for j in range(data['num_vars']):
    #         constraint.SetCoefficient(x[j], data['constraint_coeffs'][i][j])
    for i in range(data['num_constraints']-7):
      constraint_expr = [data['constraint_coeffs'][i][j] * x[j] for j in range(data['num_vars'])]
      solver.Add(sum(constraint_expr) == data['bounds'][i])
    for i in range(data['num_constraints']-7, data['num_constraints']):
      constraint_expr = [data['constraint_coeffs'][i][j] * x[j] for j in range(data['num_vars'])]
      solver.Add(sum(constraint_expr) <= data['bounds'][i])     
    print('Number of constraints =', solver.NumConstraints())
    # In Python, you can also set the constraints as follows.
    # for i in range(data['num_constraints']):
    #  constraint_expr = \
    # [data['constraint_coeffs'][i][j] * x[j] for j in range(data['num_vars'])]
    #  solver.Add(sum(constraint_expr) <= data['bounds'][i])

    objective = solver.Objective()
    for j in range(data['num_vars']):
        objective.SetCoefficient(x[j], data['obj_coeffs'][j])
    objective.SetMinimization()
    # In Python, you can also set the objective as follows.
    # obj_expr = [data['obj_coeffs'][j] * x[j] for j in range(data['num_vars'])]
    # solver.Maximize(solver.Sum(obj_expr))

    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        print('Objective value =', solver.Objective().Value())
        for j in range(data['num_vars']):
            print(x[j].name(), ' = ', x[j].solution_value())
        print()
        print('Problem solved in %f milliseconds' % solver.wall_time())
        print('Problem solved in %d iterations' % solver.iterations())
        print('Problem solved in %d branch-and-bound nodes' % solver.nodes())
    else:
        print('The problem does not have an optimal solution.')


if __name__ == '__main__':
    main()
 



