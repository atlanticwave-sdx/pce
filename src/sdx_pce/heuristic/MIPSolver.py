
class MIPSolver:

    def Variable(self, type):
        return None

    def Assert(self, constraint):
        pass

    def Maximize(self, objective):
        pass

    def Solve(self):
        pass

    def Value(self, variable):
        return None

from ortools.linear_solver import pywraplp

class GORSolver(MIPSolver):
    def __init__(self):
        self.constraints = []
        self.objective = None
        self.solver = pywraplp.Solver.CreateSolver("GLOP")
        #self.solver = pywraplp.Solver.CreateSolver("PDLP")

    def variable(self, var):
        x = self.solver.Var(0, self.solver.infinity(), False, var)
        return x
    
    def Maximize(self,objective):
        self.objective = objective

    def Solve(self):
        assert self.objective
        status = self.solver.Solve()             
        return  status


import cvxpy as cp

class CvxSolver(MIPSolver):
    def __init__(self):
        self.constraints = []
        self.objective = None
        self.problem = None

    def variable(self, var):
        v_flow = self.Variable()
        self.Assert(v_flow >= 0)
        return v_flow

    def Variable(self, type = None):
        if type == "Int":
            return cp.Variable(integer = True)            
        if type == "Bool":
            return cp.Variable(boolean = True)
        return cp.Variable(1)        

    def Maximize(self, objective):
        self.objective = cp.Maximize(objective)

    def Assert(self, constraint):
        self.constraints.append(constraint)

    def Solve(self):
        assert self.objective
        prob = cp.Problem(self.objective, self.constraints)
        self.problem = prob
        print(f"NumVariables:{len(self.problem.variables())}")
        print(f"NumConstraints:{len(self.problem.constraints)}")
        return  prob.solve()

    def Value(self, var):
        return var.value

    def __repr__(self):
        return ""
