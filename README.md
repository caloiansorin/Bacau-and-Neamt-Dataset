# Bacău & Neamț Truck-and-Drone Dataset

[![Code: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![Data: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
![Python](https://img.shields.io/badge/python-%E2%89%A53.10-3776AB.svg)

A real-world regional instance for **truck-and-drone delivery routing**, built on **176 localities** in Bacău and Neamț counties, Romania. The repository contains the node data, the optimal truck-only tour, the full source code of the capacity-constrained heuristic, and all experimental results reported in the associated article.

> **Associated article**
> S.-I. Caloian, G.C. Crișan. *A Capacity-Constrained Heuristic Approach for Asynchronous Truck-and-Drone Delivery Systems Across Regional Networks.* Submitted to *Drones* (MDPI), 2026.

---

## Table of contents

- [The dataset](#the-dataset)
- [Road-distance matrix (not included)](#road-distance-matrix-not-included)
- [Repository structure](#repository-structure)
- [Reproducing the experiments](#reproducing-the-experiments)
- [Main results](#main-results)
- [License](#license)

---

## The dataset

| Property | Value |
|---|---|
| Nodes | 176 (1 depot + 175 customers) |
| Depot | node 1 — Bacău |
| Region | Bacău county (93 nodes) and Neamț county (83 nodes), Romania |
| Bounding box | lat 46.11° – 47.32° N, lon 25.78° – 27.39° E |
| Truck distances | real road-network distances (meters) — see below |
| Drone distances | Haversine great-circle distance, R = 6371 km |
| Customer demands | U(0, 5) kg, `random.seed(42)`, mean 2.40 kg |
| Drone-ineligible customers | 68 (demand > Q<sub>max</sub> = 3 kg) |
| Baseline truck-only tour | optimal Concorde tour (NEOS Server), **2089.05 km** |

### Files in `data/`

| File | Description |
|---|---|
| `nodes_coordinates_demands.csv` | `node_id, latitude, longitude, name, demand_kg, is_depot` — the main data file |
| `Orase.xlsx` | the same nodes (ID, latitude, longitude, name), in the format read by the code |
| `ruta_optima_tsp.txt` | optimal truck-only tour, one edge per line: `from to cost_in_meters` |

---

## Road-distance matrix (not included)

The truck road distances were collected through the **Google Distance Matrix API**. Under the Google Maps Platform terms of service, these results may not be redistributed, so **the 176 × 176 distance matrix is not part of this repository**.

It can be regenerated with your own API key:

```bash
pip install googlemaps
export GOOGLE_MAPS_API_KEY=your_key          # Windows: set GOOGLE_MAPS_API_KEY=your_key
python scripts/fetch_distance_matrix.py      # writes data/matrice_distante.xlsx
```

The script applies the same preprocessing as in the article:

1. raw driving distances c<sub>ij</sub><sup>raw</sup> (possibly asymmetric);
2. symmetrization c<sub>ij</sub> = min(c<sub>ij</sub><sup>raw</sup>, c<sub>ji</sub><sup>raw</sup>);
3. rounding up to integer meters.

> **Note.** Road distances returned by the API change over time, so a newly fetched matrix may differ slightly from the one used in the article (collected in June 2025). All results obtained with the original matrix are provided in [`results/`](results).

---

## Repository structure

```
.
├── data/                         # nodes, demands, optimal truck-only tour
├── tsp_drona/                    # heuristic source code
│   ├── config.py                 #   experiment parameters and paths
│   ├── date.py                   #   data loading, Haversine, demand generation
│   ├── euristica.py              #   the heuristic (FULL) and the ablation variants
│   ├── batch.py                  #   batch execution
│   └── analiza.py                #   summary tables, Excel/TXT export
├── results/
│   ├── rezumat_toate_scenariile.xlsx          # the 36 FULL configurations
│   ├── Folder {1,2,3} - Set … - AD{10,20,30}/ # detailed log of every FULL run
│   └── Ablation Study/
│       ├── ablation_study.xlsx                # all 144 runs + comparisons vs FULL
│       ├── rezumat_ablation.txt
│       └── AD{10,20,30}/                      # detailed log of every ablation run
├── scripts/fetch_distance_matrix.py           # regenerates the road-distance matrix
└── main.py                                    # runs everything
```

Code identifiers and log messages are in Romanian:

| Romanian | English |
|---|---|
| camion / dronă | truck / drone |
| cerere, payload | demand, package mass |
| misiune | drone mission (sortie) |
| economie | saving relative to the truck-only baseline |
| cost total sistem | total system cost |
| autonomie | drone autonomy (AD) |

---

## Reproducing the experiments

```bash
pip install -r requirements.txt
# place data/matrice_distante.xlsx (see above), then:
python main.py                      # 36 FULL scenarios + ablation study -> ./results
python main.py --fara-ablation      # only the 36 FULL scenarios
```

### How the heuristic works

1. **Stage 1 — truck backbone.** The optimal truck-only tour is computed with Concorde.
2. **Stage 2 — drone substitution.** The tour is scanned in order. For three consecutive nodes (i−1, i, i+1), customer *i* is served by an out-and-back drone sortie from node i−1 if:
   - its package fits: q<sub>i</sub> ≤ Q<sub>max</sub>;
   - the round trip fits the autonomy: 2·d<sub>i−1,i</sub> ≤ AD;
   - it is economically worth it: 2·d<sub>i−1,i</sub> / α + SL + SR **<** c<sub>i−1,i</sub> + c<sub>i,i+1</sub> − c<sub>i−1,i+1</sub>.

### Experiment grid

| Parameter | Meaning | Values |
|---|---|---|
| `SL = SR` | launch / recovery penalty (km-equivalent) | 0, 0.5, 1, 1.5 |
| `alpha` | drone efficiency factor | 2, 3, 4 |
| `AD` | drone autonomy (km) | 10, 20, 30 |
| `Q_max` | drone payload capacity (kg) | 3 |

4 × 3 × 3 = **36 configurations**, each evaluated with the full heuristic and three ablation / constraint-removal variants (**144 runs**).

---

## Main results

| Variant | Mean system cost (km) | Mean gain (%) | Mean drone missions |
|---|---:|---:|---:|
| **FULL** (proposed) | **1989.93** | **4.74** | 19.22 |
| NO_ECONOMIC_FILTER | 2231.14 | −6.80 | 58.33 |
| NO_ENDURANCE_CONSTRAINT | 1914.57 | 8.35 | 29.50 |
| NO_PAYLOAD_CONSTRAINT | 1929.22 | 7.65 | 28.08 |

- Best configuration: `SL = SR = 0`, `alpha = 4`, `AD = 30 km` — **11.45%** cost reduction with 43 drone missions.
- Removing the economic acceptance criterion triples drone usage but makes the system **worse** than the truck-only baseline.

---

## License

- **Code** — [MIT License](LICENSE)
- **Data and results** — [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)

## Contact

**Sorin-Ionut Caloian** — sorin.caloian@ub.ro
Faculty of Sciences, "Vasile Alecsandri" University of Bacău, Romania
