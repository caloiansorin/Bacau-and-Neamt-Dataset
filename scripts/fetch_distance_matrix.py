"""Regenerates data/matrice_distante.xlsx (road distances, in meters) with the Google Distance Matrix API.

The matrix itself is not distributed in this repository because of the Google Maps Platform
terms of service. Running this script with your own API key rebuilds it.

Usage:
    pip install googlemaps
    export GOOGLE_MAPS_API_KEY=...        # Windows: set GOOGLE_MAPS_API_KEY=...
    python scripts/fetch_distance_matrix.py

Steps (as described in the manuscript):
    1. raw driving distances c_ij^raw between all 176 nodes (may be asymmetric);
    2. symmetrization: c_ij^sym = min(c_ij^raw, c_ji^raw);
    3. integer weights: c_ij = ceil(c_ij^sym).

Note: Google road distances change over time (road works, new roads), so a matrix fetched today
may differ slightly from the one used in the paper (fetched in June 2025).
"""

import math
import os
import time
from pathlib import Path

import googlemaps
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV_NODURI = ROOT / "data" / "nodes_coordinates_demands.csv"
CALE_MATRICE = ROOT / "data" / "matrice_distante.xlsx"

# Limita API: maxim 25 origini / destinatii si 100 de elemente pe cerere
BLOC = 10


def main():
    cheie = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not cheie:
        raise SystemExit("Set the GOOGLE_MAPS_API_KEY environment variable first.")

    client = googlemaps.Client(key=cheie)

    noduri = pd.read_csv(CSV_NODURI)
    ids = noduri["node_id"].tolist()
    coordonate = list(zip(noduri["latitude"], noduri["longitude"]))
    n = len(ids)

    raw = [[0.0] * n for _ in range(n)]

    for i0 in range(0, n, BLOC):
        for j0 in range(0, n, BLOC):
            raspuns = client.distance_matrix(
                origins=coordonate[i0:i0 + BLOC],
                destinations=coordonate[j0:j0 + BLOC],
                mode="driving",
            )
            for di, rand in enumerate(raspuns["rows"]):
                for dj, element in enumerate(rand["elements"]):
                    i, j = i0 + di, j0 + dj
                    if i != j:
                        raw[i][j] = element["distance"]["value"] if element["status"] == "OK" else math.inf
            time.sleep(0.1)
        print(f"rows {i0 + 1}-{min(i0 + BLOC, n)} / {n} done")

    simetric = [
        [0.0 if i == j else float(math.ceil(min(raw[i][j], raw[j][i]))) for j in range(n)]
        for i in range(n)
    ]

    pd.DataFrame(simetric, index=ids, columns=ids).to_excel(CALE_MATRICE)
    print(f"Saved: {CALE_MATRICE}")


if __name__ == "__main__":
    main()
