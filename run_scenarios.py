import csv
import os
import math
from data_loader import CivilDataLoader
from vrp_model import GurobiVRPSolver

base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "data")
time_limit = 60 # 1 minute per scenario to generate data fast
num_stores = 20

loader = CivilDataLoader(data_dir=data_dir)

scenarios = []

print("Running Scenario 1: Base Case")
data = loader.load_and_process(week_num=1, max_stores=num_stores)
solver = GurobiVRPSolver(data, time_limit=time_limit)
solver.build_model()
solver.solve()
base_vehicles = solver.num_vehicles
truck_routes = sum(1 for r in solver.solution['routes'])
scenarios.append({
    "Scenario": "1. Base Case",
    "Description": "Baseline parameters (20 stores)",
    "Total Cost (TL)": solver.solution['costs']['total'],
    "Gap (%)": round(solver.solution['gap'], 2),
    "Truck Routes Used": truck_routes,
    "Cargo Outsource Count": solver.solution['cargo_nodes']
})

print("Running Scenario 2: Peak Holiday (+20% Demand)")
data_high_dem = loader.load_and_process(week_num=1, max_stores=num_stores, demand_multiplier=1.20)
solver2 = GurobiVRPSolver(data_high_dem, time_limit=time_limit)
solver2.build_model()
solver2.solve()
scenarios.append({
    "Scenario": "2. Holiday Peak",
    "Description": "+20% volume per store",
    "Total Cost (TL)": solver2.solution['costs']['total'],
    "Gap (%)": round(solver2.solution['gap'], 2),
    "Truck Routes Used": sum(1 for r in solver2.solution['routes']),
    "Cargo Outsource Count": solver2.solution['cargo_nodes']
})

print("Running Scenario 3: Limited Fleet (-30% Capacity)")
# Reduce fleet by 30% from the nominal baseline
restricted_fleet = math.floor(base_vehicles * 0.70)
data_limited_fleet = loader.load_and_process(week_num=1, max_stores=num_stores)
solver3 = GurobiVRPSolver(data_limited_fleet, time_limit=time_limit, vehicle_limit=restricted_fleet)
solver3.build_model()
solver3.solve()
scenarios.append({
    "Scenario": "3. Fleet Shortage",
    "Description": f"Vehicles strict limit to {restricted_fleet}",
    "Total Cost (TL)": solver3.solution['costs']['total'],
    "Gap (%)": round(solver3.solution['gap'], 2),
    "Truck Routes Used": sum(1 for r in solver3.solution['routes']),
    "Cargo Outsource Count": solver3.solution['cargo_nodes']
})

print("Running Scenario 4: Fuel Surge (+30% Cost)")
data_fuel_surge = loader.load_and_process(week_num=1, max_stores=num_stores, transport_multiplier=1.30)
solver4 = GurobiVRPSolver(data_fuel_surge, time_limit=time_limit)
solver4.build_model()
solver4.solve()
scenarios.append({
    "Scenario": "4. Fuel Surge",
    "Description": "+30% transportation rate cost",
    "Total Cost (TL)": solver4.solution['costs']['total'],
    "Gap (%)": round(solver4.solution['gap'], 2),
    "Truck Routes Used": sum(1 for r in solver4.solution['routes']),
    "Cargo Outsource Count": solver4.solution['cargo_nodes']
})

# Write to CSV
file_path = os.path.join(base_dir, "scenario_analysis_report.csv")
with open(file_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=scenarios[0].keys())
    writer.writeheader()
    writer.writerows(scenarios)

print(f"\nScenario analysis generated successfully at: {file_path}")
