import json
import csv
import math
import os

class CivilDataLoader:
    """
    Handles extracting, computing, and structuring raw VRP data 
    from CSV/JSON files into a mathematics-ready payload for solvers.
    """
    
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.capacity = 6
        
    @staticmethod
    def haversine(lon1, lat1, lon2, lat2):
        lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return 6371 * c
        
    def _load_raw_data(self, week_num):
        with open(os.path.join(self.data_dir, "civil_stores.json"), 'r', encoding='utf-8') as f:
            store_data = json.load(f)
            
        demands_data = {}
        with open(os.path.join(self.data_dir, "civil_sevkiyat_full.csv"), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Hafta'].strip() == f"{week_num}.Hafta":
                    demands_data[row['Mağaza'].strip()] = {
                        'pallets': int(row['Palet Adet']),
                        'desi': int(row['Toplam Desi'].replace('.', ''))
                    }
                    
        shipping_rates = {}
        with open(os.path.join(self.data_dir, "newshippingcost.csv"), 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                city = row[0].strip().upper()
                rate = float(row[1].replace(',', '.'))
                shipping_rates[city] = rate
                
        return store_data, demands_data, shipping_rates

    def load_and_process(self, week_num=1, max_stores=30):
        store_data, demands_data, shipping_rates = self._load_raw_data(week_num)
        
        depot = store_data['depot']
        all_stores = store_data['stores']
        
        # Geographically diverse subset selection
        if len(all_stores) > max_stores:
            for s in all_stores:
                s['dist_depot'] = self.haversine(depot['lon'], depot['lat'], s['lon'], s['lat']) * 1.3
            all_stores_sorted = sorted(all_stores, key=lambda s: s['dist_depot'])
            
            step = len(all_stores_sorted) / max_stores
            selected = []
            for i in range(max_stores):
                idx = min(int(i * step), len(all_stores_sorted) - 1)
                if all_stores_sorted[idx] not in selected:
                    selected.append(all_stores_sorted[idx])
            for s in all_stores_sorted:
                if len(selected) >= max_stores: break
                if s not in selected: selected.append(s)
            stores = selected[:max_stores]
        else:
            stores = all_stores
            
        city_normalize = {"İstanbul": "ISTANBUL ANADOLU", "Adana": "ADANA", "Ankara": "ANKARA", "Antalya": "ANTALYA"}
        def get_istanbul_key(lon): return "ISTANBUL ANADOLU" if lon >= 29.0 else "ISTANBUL AVRUPA"

        # Initialize node structure
        split_locations = [f"Depot ({depot['city']})"]
        split_coords = [(depot['lat'], depot['lon'])]
        split_demands = {0: 0}
        split_cargo_costs = {0: 0.0}
        
        node_id = 1
        for i, s in enumerate(stores):
            full_name = f"{s['city']} {s['name']}"
            sd = demands_data.get(full_name, {'pallets': 2, 'desi': 500})
            
            pallets = sd['pallets']
            desi = sd['desi']
            city = s['city']
            
            csv_key = get_istanbul_key(s['lon']) if city == "İstanbul" else city_normalize.get(city, city.upper())
            rate = shipping_rates.get(csv_key, 6.00) * 1.30
            
            if pallets <= self.capacity:
                split_locations.append(f"{s['city']} / {s['name']}")
                split_coords.append((s['lat'], s['lon']))
                split_demands[node_id] = pallets
                split_cargo_costs[node_id] = round(desi * rate, 2)
                node_id += 1
            else:
                remaining = pallets
                chunk_idx = 0
                while remaining > 0:
                    chunk = min(remaining, self.capacity)
                    split_locations.append(f"{s['city']} / {s['name']} (part {chunk_idx+1})")
                    split_coords.append((s['lat'], s['lon']))
                    split_demands[node_id] = chunk
                    split_cargo_costs[node_id] = round((desi / pallets) * chunk * rate, 2)
                    
                    remaining -= chunk
                    chunk_idx += 1
                    node_id += 1
                    
        n_split = node_id
        
        # Compile mathematical matrices
        dist_matrix = {}
        empty_cost_matrix = {}
        loaded_cost_matrix = {}
        
        for i in range(n_split):
            for j in range(n_split):
                if i != j:
                    d = self.haversine(split_coords[i][1], split_coords[i][0], split_coords[j][1], split_coords[j][0]) * 1.3
                    dist_matrix[i, j] = round(d, 1)
                    if j == 0:
                        empty_cost_matrix[i, j] = round(d * 8, 2) # Empty return
                    else:
                        loaded_cost_matrix[i, j] = round(d * 9, 2) # Loaded travel

        return {
            'num_nodes': n_split,
            'capacity': self.capacity,
            'locations': split_locations,
            'coords': split_coords,
            'demands': split_demands,
            'cargo_costs': split_cargo_costs,
            'dist_matrix': dist_matrix,
            'empty_cost_matrix': empty_cost_matrix,
            'loaded_cost_matrix': loaded_cost_matrix
        }
