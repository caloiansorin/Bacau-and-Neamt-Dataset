"""Euristica camion + drona (misiuni simple) si variantele de ablation.

LOGICA ORIGINALA A EURISTICII ESTE NEMODIFICATA (run_scenario = FULL).
Sunt adaugate DOAR doua statistici de raportare pentru FULL:
    - distanta_totala_zbor_km
    - payload_total_drona_kg

ABLATION (run_scenario_ablation) - aceeasi logica de rutare, dar se elimina DOAR:
    NO_ECONOMIC_FILTER       conditia  cost_drona_1 < economie_reala_simpla
    NO_ENDURANCE_CONSTRAINT  conditia  total_dist > AD
    NO_PAYLOAD_CONSTRAINT    conditia  payload > max_payload

Rutarea camionului, ordinea clientilor, eliminarea nodurilor,
formula costului dronei si mecanismul greedy NU sunt modificate.
"""

import time

from .config import MAX_DRONE_PAYLOAD_KG
from .date import get_air_distance, get_truck_direct_segment_cost_km

VARIANTA_FULL = "FULL"
VARIANTA_NO_ECONOMIC = "NO_ECONOMIC_FILTER"
VARIANTA_NO_ENDURANCE = "NO_ENDURANCE_CONSTRAINT"
VARIANTA_NO_PAYLOAD = "NO_PAYLOAD_CONSTRAINT"

VARIANTE_ABLATION = [VARIANTA_NO_ECONOMIC, VARIANTA_NO_ENDURANCE, VARIANTA_NO_PAYLOAD]


def calculate_single_drop(
    launch_node, client, AD, SL, SR, alpha, cereri, max_payload, coordonate,
    verifica_payload=True, verifica_autonomie=True,
):
    """Cost si distanta de zbor pentru o misiune simpla de drona.

    verifica_payload=False   -> ablation NO_PAYLOAD_CONSTRAINT (se elimina doar payload > max_payload)
    verifica_autonomie=False -> ablation NO_ENDURANCE_CONSTRAINT (se elimina doar total_dist > AD)
    """
    payload = cereri.get(client, float('inf'))

    if (verifica_payload and payload > max_payload) or launch_node == client:
        return float('inf'), float('inf')

    dist_one_way = get_air_distance(launch_node, client, coordonate)
    total_dist = 2 * dist_one_way

    if verifica_autonomie and total_dist > AD:
        return float('inf'), float('inf')

    cost = total_dist / alpha + SL + SR

    return cost, total_dist


def _calcul_drona(date, varianta, current_truck_loc, j1, AD, SL, SR, alpha):
    return calculate_single_drop(
        current_truck_loc, j1, AD, SL, SR, alpha,
        date.cereri_clienti, MAX_DRONE_PAYLOAD_KG, date.coordonate,
        verifica_payload=(varianta != VARIANTA_NO_PAYLOAD),
        verifica_autonomie=(varianta != VARIANTA_NO_ENDURANCE),
    )


def _curata_ruta(optimized_truck_path):
    final_truck_route_cleaned = []
    if optimized_truck_path:
        final_truck_route_cleaned.append(optimized_truck_path[0])
        for node in optimized_truck_path[1:]:
            if node != final_truck_route_cleaned[-1]:
                final_truck_route_cleaned.append(node)
    return final_truck_route_cleaned


def _cost_ruta_camion(ruta, df_dist):
    if len(ruta) <= 1:
        return 0
    return sum(
        get_truck_direct_segment_cost_km(ruta[i], ruta[i + 1], df_dist)
        for i in range(len(ruta) - 1)
    )


# ============================================================
# FULL: un singur scenariu (SL, SR, alpha, AD) - logica originala
# ============================================================

def run_scenario(date, SL, SR, alpha, AD):
    timp_start = time.perf_counter()

    df_dist = date.df_dist
    cereri_clienti = date.cereri_clienti
    ruta_camion_noduri_initial = date.ruta_camion_noduri_initial
    depozit_idx = date.depozit_idx
    initial_truck_cost_km = date.initial_truck_cost_km

    print(
        f"Parametri: SL=SR={SL}; "
        f"alpha={alpha}; "
        f"AD={AD} km; "
        f"Q_max={MAX_DRONE_PAYLOAD_KG} kg"
    )
    print(f"Cost TSP initial Camion: {initial_truck_cost_km:.2f} km")

    print("\n--- Greutati generate (cereri clienti, kg) ---")
    for node in date.all_known_node_ids:
        eticheta = " (DEPOZIT)" if node == depozit_idx else ""
        print(f"Nod {node}{eticheta}: {cereri_clienti[node]:.2f} kg")

    print("\n--- PASUL 2: Optimizarea Rutei Camionului cu Drone (misiuni simple) ---")

    customers_served_by_drone = set()
    all_drone_missions = []
    optimized_truck_path = []

    esecuri_payload = 0
    esecuri_autonomie = 0
    esecuri_economie = 0

    current_truck_loc = (
        ruta_camion_noduri_initial[0] if ruta_camion_noduri_initial else depozit_idx
    )
    optimized_truck_path.append(current_truck_loc)

    idx = 0
    n_segments = len(ruta_camion_noduri_initial) - 1

    while idx < n_segments:
        j1 = ruta_camion_noduri_initial[idx + 1]
        k_after_j1 = ruta_camion_noduri_initial[idx + 2] if (idx + 2 <= n_segments) else None

        action_taken = False

        if k_after_j1 is not None and j1 != depozit_idx:
            payload_j1 = cereri_clienti.get(j1, float('inf'))

            if payload_j1 > MAX_DRONE_PAYLOAD_KG:
                esecuri_payload += 1

            cost_drona_1, dist_zbor_1 = _calcul_drona(
                date, VARIANTA_FULL, current_truck_loc, j1, AD, SL, SR, alpha
            )

            if cost_drona_1 != float('inf'):
                cost_camion_cu_j1 = (
                    get_truck_direct_segment_cost_km(current_truck_loc, j1, df_dist)
                    + get_truck_direct_segment_cost_km(j1, k_after_j1, df_dist)
                )
                cost_camion_fara_j1 = get_truck_direct_segment_cost_km(
                    current_truck_loc, k_after_j1, df_dist
                )
                economie_reala_simpla = cost_camion_cu_j1 - cost_camion_fara_j1

                if cost_drona_1 < economie_reala_simpla:
                    customers_served_by_drone.add(j1)
                    all_drone_missions.append({
                        'type': 'SINGLE',
                        'launch_node': current_truck_loc,
                        'clients': [j1],
                        'cost': cost_drona_1,
                        'flight_dist': dist_zbor_1,
                        'payload': cereri_clienti[j1]
                    })

                    print(
                        f"{idx+1}\t"
                        f"[DRONA SIMPLA] "
                        f"Din {current_truck_loc} -> {j1}\t"
                        f"ZBOR: {dist_zbor_1:.2f} km | "
                        f"MASA: {cereri_clienti[j1]:.2f} kg | "
                        f"COST DRONA: {cost_drona_1:.2f} km | "
                        f"ECONOMIE NETA: "
                        f"{economie_reala_simpla - cost_drona_1:.2f} km"
                    )

                    idx += 1
                    action_taken = True
                    continue

                else:
                    esecuri_economie += 1

            elif payload_j1 <= MAX_DRONE_PAYLOAD_KG:
                esecuri_autonomie += 1

        if not action_taken:
            next_node = j1
            if current_truck_loc != next_node:
                cost_segment = get_truck_direct_segment_cost_km(
                    current_truck_loc, next_node, df_dist
                )
                print(
                    f"{idx+1}\t"
                    f"[CAMION] "
                    f"{current_truck_loc} -> "
                    f"{next_node}\t"
                    f"COST TRUCK: "
                    f"{cost_segment:.2f} km"
                )
                current_truck_loc = next_node
                optimized_truck_path.append(current_truck_loc)

            idx += 1

    print("\n--- Rezultate Finale ---")

    final_truck_route_cleaned = _curata_ruta(optimized_truck_path)
    actual_truck_path_cost_km = _cost_ruta_camion(final_truck_route_cleaned, df_dist)

    total_drone_mission_cost = sum(m['cost'] for m in all_drone_missions)

    # Statistici suplimentare FULL: calculate DOAR din misiunile deja acceptate.
    # Nu modifica in niciun fel logica de selectie, rutarea sau costurile.
    total_flight_distance = sum(m['flight_dist'] for m in all_drone_missions)
    total_payload_drone = sum(m['payload'] for m in all_drone_missions)

    total_system_cost = actual_truck_path_cost_km + total_drone_mission_cost

    customers_served_by_truck = (
        set(date.all_known_node_ids) - customers_served_by_drone - {depozit_idx}
    )

    print(
        f"\nRuta Camionului "
        f"({len(final_truck_route_cleaned)} noduri):\n"
        f"{' -> '.join(map(str, final_truck_route_cleaned))}"
    )
    print(
        f"\nClienti deserviti de Drona "
        f"({len(customers_served_by_drone)}): "
        f"{sorted(list(customers_served_by_drone))}"
    )
    print(
        f"Clienti deserviti de Camion "
        f"({len(customers_served_by_truck)}): "
        f"{sorted(list(customers_served_by_truck))}"
    )

    print("\n--- Statistici Performanta ---")
    print(f"Numar total misiuni drona: {len(all_drone_missions)} (toate SINGLE)")
    print(f"Cost initial TSP pur: {initial_truck_cost_km:.2f} km")
    print(f"Cost efectiv traseu Camion: {actual_truck_path_cost_km:.2f} km")
    print(f"Cost total misiuni Drona: {total_drone_mission_cost:.2f} km")
    print(f"COST TOTAL SISTEM (Camion + Drona): {total_system_cost:.2f} km")
    print(f"Distanta totala zbor drona: {total_flight_distance:.2f} km")
    print(f"Payload total transportat de drona: {total_payload_drone:.2f} kg")

    if initial_truck_cost_km:
        economie_km = initial_truck_cost_km - total_system_cost
        economie_procent = economie_km / initial_truck_cost_km * 100
        print(f"ECONOMIE REALA ABSOLUTA: {economie_km:.2f} km ({economie_procent:.2f}%)")
    else:
        economie_km = None
        economie_procent = None

    print("\n--- Diagnostic Esecuri Misiune Simpla (candidati j1 evaluati) ---")
    print(f"Esecuri din cauza payload-ului (> {MAX_DRONE_PAYLOAD_KG} kg): {esecuri_payload}")
    print(f"Esecuri din cauza autonomiei (zbor dus-intors > {AD} km): {esecuri_autonomie}")
    print(f"Esecuri din cauza economiei nete (cost drona >= economie): {esecuri_economie}")

    timp_executie_sec = time.perf_counter() - timp_start

    print(f"\nTimp de executie scenariu: {timp_executie_sec:.4f} secunde")

    return {
        'SL_SR': SL,
        'alpha': alpha,
        'AD': AD,
        'cost_tsp_initial_km': initial_truck_cost_km,
        'cost_camion_final_km': actual_truck_path_cost_km,
        'cost_misiuni_drona_km': total_drone_mission_cost,
        'cost_total_sistem_km': total_system_cost,
        'economie_km': round(economie_km, 2) if economie_km is not None else None,
        'economie_procent': round(economie_procent, 2) if economie_procent is not None else None,
        'nr_misiuni_drona': len(all_drone_missions),
        'nr_clienti_drona': len(customers_served_by_drone),
        'nr_clienti_camion': len(customers_served_by_truck),
        # Statistici suplimentare de raportare. Nu influenteaza algoritmul sau rezultatele.
        'distanta_totala_zbor_km': round(total_flight_distance, 4),
        'payload_total_drona_kg': round(total_payload_drone, 4),
        'timp_executie_sec': round(timp_executie_sec, 4),
    }


# ============================================================
# ABLATION: copie separata a logicii run_scenario()
# NU inlocuieste si NU modifica run_scenario().
# ============================================================

def run_scenario_ablation(date, SL, SR, alpha, AD, varianta):
    timp_start = time.perf_counter()

    df_dist = date.df_dist
    cereri_clienti = date.cereri_clienti
    ruta_camion_noduri_initial = date.ruta_camion_noduri_initial
    depozit_idx = date.depozit_idx
    initial_truck_cost_km = date.initial_truck_cost_km

    print(f"ABLATION: {varianta}")
    print(
        f"Parametri: "
        f"SL=SR={SL}; "
        f"alpha={alpha}; "
        f"AD={AD} km; "
        f"Q_max={MAX_DRONE_PAYLOAD_KG} kg"
    )
    print(f"Cost TSP initial Camion: {initial_truck_cost_km:.2f} km")

    customers_served_by_drone = set()
    all_drone_missions = []
    optimized_truck_path = []

    current_truck_loc = (
        ruta_camion_noduri_initial[0] if ruta_camion_noduri_initial else depozit_idx
    )
    optimized_truck_path.append(current_truck_loc)

    idx = 0
    n_segments = len(ruta_camion_noduri_initial) - 1

    # ACEEASI PARCURGERE CA IN CODUL ORIGINAL
    while idx < n_segments:
        j1 = ruta_camion_noduri_initial[idx + 1]
        k_after_j1 = ruta_camion_noduri_initial[idx + 2] if (idx + 2 <= n_segments) else None

        action_taken = False

        if k_after_j1 is not None and j1 != depozit_idx:
            cost_drona_1, dist_zbor_1 = _calcul_drona(
                date, varianta, current_truck_loc, j1, AD, SL, SR, alpha
            )

            if cost_drona_1 != float('inf'):
                cost_camion_cu_j1 = (
                    get_truck_direct_segment_cost_km(current_truck_loc, j1, df_dist)
                    + get_truck_direct_segment_cost_km(j1, k_after_j1, df_dist)
                )
                cost_camion_fara_j1 = get_truck_direct_segment_cost_km(
                    current_truck_loc, k_after_j1, df_dist
                )
                economie_reala_simpla = cost_camion_cu_j1 - cost_camion_fara_j1

                # SINGURA MODIFICARE PENTRU NO_ECONOMIC_FILTER:
                # acceptam orice misiune fezabila.
                if varianta == VARIANTA_NO_ECONOMIC:
                    accepta_misiunea = True
                else:
                    accepta_misiunea = cost_drona_1 < economie_reala_simpla

                if accepta_misiunea:
                    customers_served_by_drone.add(j1)
                    all_drone_missions.append({
                        'type': 'SINGLE',
                        'launch_node': current_truck_loc,
                        'clients': [j1],
                        'cost': cost_drona_1,
                        'flight_dist': dist_zbor_1,
                        'payload': cereri_clienti[j1]
                    })

                    print(
                        f"{idx+1}\t"
                        f"[DRONA SIMPLA] "
                        f"Din "
                        f"{current_truck_loc} "
                        f"-> "
                        f"{j1}\t"
                        f"ZBOR: "
                        f"{dist_zbor_1:.2f} km | "
                        f"MASA: "
                        f"{cereri_clienti[j1]:.2f} kg | "
                        f"COST DRONA: "
                        f"{cost_drona_1:.2f} km | "
                        f"ECONOMIE NETA: "
                        f"{economie_reala_simpla - cost_drona_1:.2f} km"
                    )

                    idx += 1
                    action_taken = True
                    continue

        # CAMION - EXACT ACEEASI LOGICA
        if not action_taken:
            next_node = j1
            if current_truck_loc != next_node:
                cost_segment = get_truck_direct_segment_cost_km(
                    current_truck_loc, next_node, df_dist
                )
                print(
                    f"{idx+1}\t"
                    f"[CAMION] "
                    f"{current_truck_loc} "
                    f"-> "
                    f"{next_node}\t"
                    f"COST TRUCK: "
                    f"{cost_segment:.2f} km"
                )
                current_truck_loc = next_node
                optimized_truck_path.append(current_truck_loc)

            idx += 1

    final_truck_route_cleaned = _curata_ruta(optimized_truck_path)
    actual_truck_path_cost_km = _cost_ruta_camion(final_truck_route_cleaned, df_dist)

    total_drone_mission_cost = sum(m['cost'] for m in all_drone_missions)
    total_system_cost = actual_truck_path_cost_km + total_drone_mission_cost

    customers_served_by_truck = (
        set(date.all_known_node_ids) - customers_served_by_drone - {depozit_idx}
    )

    if initial_truck_cost_km:
        economie_km = initial_truck_cost_km - total_system_cost
        economie_procent = economie_km / initial_truck_cost_km * 100
    else:
        economie_km = None
        economie_procent = None

    total_flight_distance = sum(m['flight_dist'] for m in all_drone_missions)
    total_payload_drone = sum(m['payload'] for m in all_drone_missions)

    print("\n--- Rezultate Ablation ---")
    print(f"Varianta: {varianta}")
    print(f"Ruta Camionului ({len(final_truck_route_cleaned)} noduri):")
    print(" -> ".join(map(str, final_truck_route_cleaned)))
    print(f"\nClienti drona: {len(customers_served_by_drone)}")
    print(f"Clienti camion: {len(customers_served_by_truck)}")
    print(f"Numar misiuni drona: {len(all_drone_missions)}")
    print(f"Cost initial TSP: {initial_truck_cost_km:.2f} km")
    print(f"Cost camion: {actual_truck_path_cost_km:.2f} km")
    print(f"Cost drona: {total_drone_mission_cost:.2f} km")
    print(f"COST TOTAL SISTEM: {total_system_cost:.2f} km")

    if economie_km is not None:
        print(f"ECONOMIE: {economie_km:.2f} km ({economie_procent:.2f}%)")

    print(f"Distanta totala zbor drona: {total_flight_distance:.2f} km")
    print(f"Payload total transportat de drona: {total_payload_drone:.2f} kg")

    timp_executie_sec = time.perf_counter() - timp_start

    print(f"Timp executie: {timp_executie_sec:.4f} secunde")

    return {
        'varianta': varianta,
        'SL_SR': SL,
        'alpha': alpha,
        'AD': AD,
        'cost_tsp_initial_km': initial_truck_cost_km,
        'cost_camion_final_km': actual_truck_path_cost_km,
        'cost_misiuni_drona_km': total_drone_mission_cost,
        'cost_total_sistem_km': total_system_cost,
        'economie_km': round(economie_km, 2) if economie_km is not None else None,
        'economie_procent': round(economie_procent, 2) if economie_procent is not None else None,
        'nr_misiuni_drona': len(all_drone_missions),
        'nr_clienti_drona': len(customers_served_by_drone),
        'nr_clienti_camion': len(customers_served_by_truck),
        'distanta_totala_zbor_km': round(total_flight_distance, 4),
        'payload_total_drona_kg': round(total_payload_drone, 4),
        'timp_executie_sec': round(timp_executie_sec, 4),
    }
