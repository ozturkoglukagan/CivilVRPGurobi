# IE401-VRP-Project-CVL

This repository contains an optimized Vehicle Routing Problem (VRP) solver using **Gurobi Optimizer** for civil logistics management. 

The project implements a Mixed Integer Linear Programming (MILP) model to solve the Capacitated Vehicle Routing Problem (CVRP) with:
- **Cargo Outsourcing:** Decisions on whether to serve a store via internal truck or third-party cargo.
- **Priority Penalties:** Time-based penalties for late deliveries after Day 2.
- **Split Deliveries:** Automatically handles stores with demand exceeding the 6-pallet truck capacity.
- **Empty Return Costs:** Differentiated cost rates for loaded travel (9 TL/km) vs empty return trips (8 TL/km).

## Project Structure

- `main.py`: The entry point for running the solver.
- `data_loader.py`: Handles data ingestion from CSV/JSON and preprocessing (Haversine distances, node splitting).
- `vrp_model.py`: Professional Object-Oriented implementation of the Gurobi model.
- `data/`: Contains raw CSV/JSON datasets (Civil store lists, demands, and shipping costs).

## Installation

### Prerequisites
- Python 3.x
- [Gurobi Optimizer](https://www.gurobi.com/)
- `gurobipy` library

### Setup
Ensure you have a valid Gurobi license installed. Then install the requirements:
```bash
pip install gurobipy
```

## Usage

Run the solver using the command line:

```bash
python3 main.py --week 1 --stores 30 --time-limit 300
```

### Optional Arguments:
- `--week`: Select week (1-4).
- `--stores`: Set max number of stores to solve.
- `--vehicles`: (Optional) Force a specific fleet size.
- `--time-limit`: Maximum time for Gurobi to optimize.

## License
MIT License
