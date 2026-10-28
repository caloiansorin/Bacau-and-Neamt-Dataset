"""Incarcarea datelor (o singura data, independent de parametri) si functiile de distanta."""

import math
import random
from dataclasses import dataclass

import pandas as pd

from . import config


@dataclass
class DateProblema:
    df_dist: pd.DataFrame
    coordonate: dict
    cereri_clienti: dict
    ruta_camion_noduri_initial: list
    segments_from_tsp_file: list
    all_known_node_ids: list
    depozit_idx: int
    initial_truck_cost_km: float


def get_truck_direct_segment_cost_km(start_node, end_node, df_dist_matrix):
    try:
        cost = df_dist_matrix.loc[start_node, end_node] / 1000.0
        if cost == 0 and start_node != end_node:
            return float('inf')
        return cost
    except KeyError:
        return float('inf')


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )

    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def get_air_distance(n1, n2, coordonate):
    if n1 not in coordonate or n2 not in coordonate:
        return float('inf')

    return haversine_distance(
        coordonate[n1][0], coordonate[n1][1],
        coordonate[n2][0], coordonate[n2][1],
    )


def citeste_ruta_tsp(cale_tsp):
    """Prelucrarea rutei camionului din TXT: linii 'i j cost_in_metri'."""
    with open(cale_tsp, 'r', encoding='utf-8') as f:
        tsp_route_lines = f.readlines()

    ruta_camion_noduri_initial = []
    segments_from_tsp_file = []

    for line in tsp_route_lines:
        parts = line.strip().split()

        if len(parts) == 3:
            try:
                i = int(parts[0])
                j = int(parts[1])
                cost_in_meters = int(parts[2])

                segments_from_tsp_file.append((i, j, cost_in_meters))

                if not ruta_camion_noduri_initial:
                    ruta_camion_noduri_initial.append(i)

                if not ruta_camion_noduri_initial or ruta_camion_noduri_initial[-1] != j:
                    ruta_camion_noduri_initial.append(j)

            except ValueError:
                continue

    return ruta_camion_noduri_initial, segments_from_tsp_file


def incarca_date(
    cale_matrice=config.CALE_MATRICE,
    cale_orase=config.CALE_ORASE,
    cale_tsp=config.CALE_TSP,
    depozit_idx=config.DEPOZIT_IDX,
    seed=config.SEED_CERERI,
):
    print("Incarc fisierele de date...")

    df_dist = pd.read_excel(cale_matrice, index_col=0)
    df_dist.index = df_dist.index.astype(int)
    df_dist.columns = df_dist.columns.astype(int)

    df_orase = pd.read_excel(
        cale_orase,
        header=None,
        names=['ID', 'Latitudine', 'Longitudine', 'Nume']
    )

    ruta_camion_noduri_initial, segments_from_tsp_file = citeste_ruta_tsp(cale_tsp)

    print("Fisiere incarcate cu succes!\n")

    all_known_node_ids = sorted(
        set(df_dist.index.tolist() + df_dist.columns.tolist())
    )

    # Cererile clientilor sunt generate O SINGURA DATA (seed fix), la fel pentru
    # toate scenariile, ca sa fie comparabile intre ele.
    random.seed(seed)

    cereri_clienti = {
        node: (
            0.0
            if node == depozit_idx
            else round(random.uniform(0, 5.0), 2)
        )
        for node in all_known_node_ids
    }

    coordonate = {
        row['ID']: (row['Latitudine'], row['Longitudine'])
        for _, row in df_orase.iterrows()
    }

    initial_truck_cost_km = sum(
        get_truck_direct_segment_cost_km(s[0], s[1], df_dist)
        for s in segments_from_tsp_file
    )

    return DateProblema(
        df_dist=df_dist,
        coordonate=coordonate,
        cereri_clienti=cereri_clienti,
        ruta_camion_noduri_initial=ruta_camion_noduri_initial,
        segments_from_tsp_file=segments_from_tsp_file,
        all_known_node_ids=all_known_node_ids,
        depozit_idx=depozit_idx,
        initial_truck_cost_km=initial_truck_cost_km,
    )
