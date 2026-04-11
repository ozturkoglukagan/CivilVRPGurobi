import argparse
import os
from data_loader import CivilDataLoader
from vrp_model import GurobiVRPSolver

def main():
    parser = argparse.ArgumentParser(description="Gurobi Exact MILP Solver for Civil VRP")
    parser.add_argument("--week", type=int, default=1, help="Week number (1-4) to load")
    parser.add_argument("--stores", type=int, default=20, help="Number of stores to solve for")
    parser.add_argument("--time-limit", type=int, default=300, help="Gurobi time limit in seconds")
    parser.add_argument("--vehicles", type=int, default=None, help="Force a specific number of vehicles (optional)")
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    
    print(f"\n[Gurobi VRP Engine] Initializing...")
    print(f"Loading Week {args.week} Data for Max {args.stores} Stores...")
    
    loader = CivilDataLoader(data_dir=data_dir)
    data = loader.load_and_process(week_num=args.week, max_stores=args.stores)
    
    print(f"Data Preprocessing Complete: Formatted {data['num_nodes']-1} isolated sub-nodes.")
    
    solver = GurobiVRPSolver(data=data, time_limit=args.time_limit, vehicle_limit=args.vehicles)
    
    print("Building mathematical constraints & arrays...")
    solver.build_model()
    
    print(f"Handing problem space to Gurobi Optimizer (Limit {args.time_limit}s)...")
    solver.solve()
    
    solver.print_summary()

if __name__ == "__main__":
    main()
