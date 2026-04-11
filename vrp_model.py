import gurobipy as gp
from gurobipy import GRB
import math

class GurobiVRPSolver:
    """
    Object-Oriented handler for precisely constructing and resolving 
    the mathematical constraints of the CVRP using Gurobi.
    """
    
    def __init__(self, data, time_limit=300, vehicle_limit=None):
        self.data = data
        self.time_limit = time_limit
        self.vehicle_limit = vehicle_limit
        self.model = None
        self.solution = None
        
        self.N = list(range(self.data['num_nodes']))
        self.S = list(range(1, self.data['num_nodes']))
        
        total_pallets = sum(self.data['demands'].values())
        if self.vehicle_limit is not None:
            self.num_vehicles = self.vehicle_limit
        else:
            self.num_vehicles = math.ceil(total_pallets / self.data['capacity']) + 2
            
        self.V = list(range(1, self.num_vehicles + 1))
        self.Q = {v: self.data['capacity'] for v in self.V}
        
    def build_model(self):
        self.model = gp.Model("VRP_Civil")
        self.model.Params.TimeLimit = self.time_limit
        self.model.Params.MIPGap = 0.05
        self.model.Params.Threads = 8
        self.model.Params.LogToConsole = 0 # Suppress noisy gurobi output directly
        
        # Variables
        self.x = self.model.addVars([(i, j, v) for i in self.N for j in self.N for v in self.V if i != j], vtype=GRB.BINARY, name="x")
        self.r = self.model.addVars(self.S, vtype=GRB.BINARY, name="r")
        self.k = self.model.addVars(self.S, vtype=GRB.BINARY, name="k")
        self.u = self.model.addVars(self.S, vtype=GRB.CONTINUOUS, lb=0, name="u")
        self.d = self.model.addVars(self.S, vtype=GRB.INTEGER, lb=1, name="d")
        self.p_delay = self.model.addVars(self.S, vtype=GRB.INTEGER, lb=0, name="p_delay")
        
        M = 100000
        penalties = {i: 100000 for i in self.S}
        
        # Objective Functions
        obj_transport = gp.quicksum(self.data['empty_cost_matrix'].get((i, j), 0) * self.x[i, j, v] for v in self.V for i in self.N for j in self.N if i != j and j == 0) + \
                        gp.quicksum(self.data['loaded_cost_matrix'].get((i, j), 0) * self.x[i, j, v] for v in self.V for i in self.N for j in self.N if i != j and j != 0)
        
        obj_cargo = gp.quicksum(self.data['cargo_costs'][i] * self.k[i] for i in self.S)
        obj_penalty = gp.quicksum(penalties[i] * (1 - self.r[i]) for i in self.S)
        obj_delay = gp.quicksum(2000 * self.p_delay[i] for i in self.S)
        
        self.model.setObjective(obj_transport + obj_cargo + obj_penalty + obj_delay, GRB.MINIMIZE)
        
        # Service constraints
        for i in self.S:
            self.model.addConstr(gp.quicksum(self.x[j, i, v] for j in self.N if j != i for v in self.V) + self.k[i] == self.r[i])
            
        # Depot constraints
        for v in self.V:
            self.model.addConstr(gp.quicksum(self.x[0, j, v] for j in self.S) <= 1)
            self.model.addConstr(gp.quicksum(self.x[i, 0, v] for i in self.S) <= 1)
            self.model.addConstr(gp.quicksum(self.x[0, j, v] for j in self.S) == gp.quicksum(self.x[i, 0, v] for i in self.S))
            
        # Flow conservation
        for i in self.S:
            for v in self.V:
                self.model.addConstr(gp.quicksum(self.x[i, j, v] for j in self.N if j != i) == gp.quicksum(self.x[j, i, v] for j in self.N if j != i))
                
        # Capacity
        for v in self.V:
            self.model.addConstr(gp.quicksum(self.data['demands'][i] * gp.quicksum(self.x[j, i, v] for j in self.N if j != i) for i in self.S) <= self.Q[v])
            
        # MTZ subtour elimination
        for i in self.S:
            self.model.addConstr(self.u[i] >= self.data['dist_matrix'][0, i] - M * (1 - gp.quicksum(self.x[0, i, v] for v in self.V)))
            for j in self.S:
                if i != j:
                    self.model.addConstr(self.u[j] >= self.u[i] + self.data['dist_matrix'][i, j] - M * (1 - gp.quicksum(self.x[i, j, v] for v in self.V)))
                    
        # Delay calculation
        for i in self.S:
            self.model.addConstr(600 * self.d[i] >= self.u[i])
            self.model.addConstr(self.p_delay[i] >= self.d[i] - 2)
            
        # Symmetry breaking
        for v in self.V[:-1]:
            self.model.addConstr(gp.quicksum(self.x[0, j, v] for j in self.S) >= gp.quicksum(self.x[0, j, v+1] for j in self.S))
            
        # Pre-assign dense nearby routes to trucks mathematically
        FORCE_TRUCK_RADIUS = 100
        for i in self.S:
            if self.data['dist_matrix'][0, i] <= FORCE_TRUCK_RADIUS and self.data['demands'][i] >= 1:
                self.model.addConstr(self.k[i] == 0)
                self.model.addConstr(self.r[i] == 1)
                
    def solve(self):
        self.model.optimize()
        if self.model.SolCount > 0:
            self._compile_solution()
        return self.solution
        
    def _compile_solution(self):
        gap = self.model.MIPGap * 100 if hasattr(self.model, 'MIPGap') else 0
        status = 'OPTIMAL' if self.model.status == GRB.OPTIMAL else 'TIME LIMIT'
        
        truck_nodes = sum(1 for i in self.S if self.k[i].x < 0.5 and self.r[i].x > 0.5)
        cargo_nodes = sum(1 for i in self.S if self.k[i].x > 0.5)
        unserved_nodes = sum(1 for i in self.S if self.r[i].x < 0.5)
        
        routes = []
        transport_cost = 0
        for v in self.V:
            if sum(self.x[0, j, v].x for j in self.S) > 0.5:
                route_path = [0]
                curr = 0
                route_dist = 0
                route_cost = 0
                route_pallets = 0
                while True:
                    next_node = None
                    for j in self.N:
                        if curr != j and self.x[curr, j, v].x > 0.5:
                            next_node = j
                            break
                    if next_node is None: break
                    
                    route_dist += self.data['dist_matrix'][curr, next_node]
                    cost_val = self.data['empty_cost_matrix'][curr, next_node] if next_node == 0 else self.data['loaded_cost_matrix'][curr, next_node]
                    route_cost += cost_val
                    
                    if next_node != 0:
                        route_pallets += self.data['demands'][next_node]
                    
                    route_path.append(next_node)
                    curr = next_node
                    if curr == 0: break
                
                transport_cost += route_cost
                routes.append({
                    'id': v,
                    'path': route_path,
                    'pallets': route_pallets,
                    'distance': route_dist,
                    'cost': route_cost
                })
                
        cargo_cost = sum(self.data['cargo_costs'][i] for i in self.S if self.k[i].x > 0.5)
        delay_cost = sum(2000 * max(0, self.p_delay[i].x) for i in self.S)
        
        self.solution = {
            'objective': self.model.objVal,
            'gap': gap,
            'runtime': self.model.Runtime,
            'status': status,
            'truck_nodes': truck_nodes,
            'cargo_nodes': cargo_nodes,
            'unserved_nodes': unserved_nodes,
            'routes': routes,
            'costs': {
                'transport': transport_cost,
                'cargo': cargo_cost,
                'delay': delay_cost,
                'total': self.model.objVal
            }
        }

    def print_summary(self):
        if not self.solution:
            print(f"❌ No feasible solution found within {self.time_limit}s.")
            return
            
        print(f"\n{'='*80}")
        print(f"  GUROBI RESULT — {self.data['num_nodes']-1} Nodes")
        print(f"{'='*80}")
        print(f"  Objective: {self.solution['objective']:,.2f} TL")
        print(f"  MIP Gap:   {self.solution['gap']:.1f}%")
        print(f"  Status:    {self.solution['status']}")
        print(f"  Time:      {self.solution['runtime']:.1f}s")
        print(f"\n  Truck deliveries: {self.solution['truck_nodes']}")
        print(f"  Cargo deliveries: {self.solution['cargo_nodes']}")
        print(f"  Unserved Nodes:   {self.solution['unserved_nodes']}")
        
        for r in self.solution['routes']:
            path_str = " → ".join([self.data['locations'][n] if n != 0 else 'Depot' for n in r['path']])
            print(f"\n  🚛 V{r['id']} [{r['pallets']}/{self.data['capacity']} plt, {r['distance']:.0f}km, {r['cost']:,.0f}₺]:\n     {path_str}")
            
        if self.solution['cargo_nodes'] > 0:
            print("\n  📦 Cargo Outsources:")
            for i in self.S:
                if self.k[i].x > 0.5:
                    print(f"     {self.data['locations'][i]} ({self.data['demands'][i]} plt, {self.data['cargo_costs'][i]:,.0f} TL)")
                    
        print(f"\n{'─'*80}")
        print(f"  COST SUMMARY")
        print(f"{'─'*80}")
        print(f"  Transportation: {self.solution['costs']['transport']:>12,.2f} TL")
        print(f"  Cargo Costs:    {self.solution['costs']['cargo']:>12,.2f} TL")
        print(f"  Delay Penalties:{self.solution['costs']['delay']:>12,.2f} TL")
        print(f"  {'─'*42}")
        print(f"  TOTAL:          {self.solution['costs']['total']:>12,.2f} TL")
        print(f"{'='*80}\n")
