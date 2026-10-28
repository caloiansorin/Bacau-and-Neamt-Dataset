"""Tabelele ablation study (rezumat, comparatie vs FULL, pivoturi) si exportul Excel / TXT."""

import os

import pandas as pd

from .euristica import (
    VARIANTA_FULL,
    VARIANTA_NO_ECONOMIC,
    VARIANTA_NO_ENDURANCE,
    VARIANTA_NO_PAYLOAD,
)

ORDINE_VARIANTE = {
    VARIANTA_FULL: 0,
    VARIANTA_NO_ECONOMIC: 1,
    VARIANTA_NO_ENDURANCE: 2,
    VARIANTA_NO_PAYLOAD: 3,
}


def construieste_tabele(rezultate_ablation):
    df_ablation = pd.DataFrame(rezultate_ablation)

    # Ordonare: pentru fiecare configuratie FULL, NO_ECONOMIC, NO_ENDURANCE, NO_PAYLOAD
    df_ablation['_ordine_varianta'] = df_ablation['varianta'].map(ORDINE_VARIANTE)
    df_ablation = (
        df_ablation
        .sort_values(by=['AD', 'alpha', 'SL_SR', '_ordine_varianta'])
        .drop(columns=['_ordine_varianta'])
        .reset_index(drop=True)
    )

    # Rezumat mediu pe varianta
    df_ablation_summary = df_ablation.groupby('varianta', as_index=False).agg(
        nr_scenarii=('varianta', 'size'),
        cost_total_mediu=('cost_total_sistem_km', 'mean'),
        cost_total_std=('cost_total_sistem_km', 'std'),
        economie_km_medie=('economie_km', 'mean'),
        gain_mediu_proc=('economie_procent', 'mean'),
        gain_median_proc=('economie_procent', 'median'),
        gain_std_proc=('economie_procent', 'std'),
        gain_min_proc=('economie_procent', 'min'),
        gain_max_proc=('economie_procent', 'max'),
        misiuni_drona_medie=('nr_misiuni_drona', 'mean'),
        clienti_drona_medie=('nr_clienti_drona', 'mean'),
    )

    # Comparatie fiecare ablation vs FULL, pentru configuratii identice (SL/SR, alpha, AD)
    df_full = (
        df_ablation[df_ablation['varianta'] == VARIANTA_FULL]
        [['SL_SR', 'alpha', 'AD', 'cost_total_sistem_km', 'economie_procent', 'nr_misiuni_drona']]
        .copy()
        .rename(columns={
            'cost_total_sistem_km': 'FULL_cost_total_sistem_km',
            'economie_procent': 'FULL_economie_procent',
            'nr_misiuni_drona': 'FULL_nr_misiuni_drona',
        })
    )
    df_fara_full = df_ablation[df_ablation['varianta'] != VARIANTA_FULL].copy()

    df_comparatie_ablation = pd.merge(
        df_fara_full, df_full, on=['SL_SR', 'alpha', 'AD'], how='left'
    )

    # pozitiv: ablation are cost mai mare decat FULL
    df_comparatie_ablation['delta_cost_vs_FULL_km'] = (
        df_comparatie_ablation['cost_total_sistem_km']
        - df_comparatie_ablation['FULL_cost_total_sistem_km']
    )
    # in PUNCTE PROCENTUALE (FULL = 15%, ablation = 10% -> -5 pp)
    df_comparatie_ablation['delta_gain_vs_FULL_pp'] = (
        df_comparatie_ablation['economie_procent']
        - df_comparatie_ablation['FULL_economie_procent']
    )
    df_comparatie_ablation['delta_misiuni_vs_FULL'] = (
        df_comparatie_ablation['nr_misiuni_drona']
        - df_comparatie_ablation['FULL_nr_misiuni_drona']
    )

    # Impact mediu fata de FULL
    df_impact_mediu = df_comparatie_ablation.groupby('varianta', as_index=False).agg(
        delta_cost_mediu_vs_FULL_km=('delta_cost_vs_FULL_km', 'mean'),
        delta_cost_median_vs_FULL_km=('delta_cost_vs_FULL_km', 'median'),
        delta_gain_mediu_vs_FULL_pp=('delta_gain_vs_FULL_pp', 'mean'),
        delta_gain_median_vs_FULL_pp=('delta_gain_vs_FULL_pp', 'median'),
        delta_gain_min_vs_FULL_pp=('delta_gain_vs_FULL_pp', 'min'),
        delta_gain_max_vs_FULL_pp=('delta_gain_vs_FULL_pp', 'max'),
        delta_misiuni_medie_vs_FULL=('delta_misiuni_vs_FULL', 'mean'),
    )

    def pivot(valoare):
        return df_ablation.pivot_table(
            index=['SL_SR', 'alpha', 'AD'], columns='varianta', values=valoare
        ).reset_index()

    return {
        'Toate rezultatele': df_ablation,               # 36 FULL + 108 ablation
        'Rezumat variante': df_ablation_summary,
        'Comparatie vs FULL': df_comparatie_ablation,
        'Impact mediu': df_impact_mediu,
        'Gain comparativ': pivot('economie_procent'),
        'Cost comparativ': pivot('cost_total_sistem_km'),
        'Misiuni comparativ': pivot('nr_misiuni_drona'),
    }


def exporta_excel(tabele, cale_excel):
    with pd.ExcelWriter(cale_excel, engine='openpyxl') as writer:
        for nume_sheet, df in tabele.items():
            df.to_excel(writer, sheet_name=nume_sheet, index=False)


def scrie_raport_txt(tabele, cale_raport, timp_total_ablation):
    df_ablation_summary = tabele['Rezumat variante']
    df_impact_mediu = tabele['Impact mediu']
    separator = "=" * 75 + "\n\n"

    with open(cale_raport, 'w', encoding='utf-8') as f:
        f.write("ABLATION STUDY - TRUCK + DRONE HEURISTIC\n")
        f.write(separator)
        f.write("FULL = codul original, fara nicio modificare.\n\n")
        f.write(
            "NO_ECONOMIC_FILTER:\n"
            "  Payload: ACTIV\n"
            "  Autonomie: ACTIVA\n"
            "  Filtru economic: ELIMINAT\n\n"
        )
        f.write(
            "NO_ENDURANCE_CONSTRAINT:\n"
            "  Payload: ACTIV\n"
            "  Autonomie: ELIMINATA\n"
            "  Filtru economic: ACTIV\n\n"
        )
        f.write(
            "NO_PAYLOAD_CONSTRAINT:\n"
            "  Payload: ELIMINAT\n"
            "  Autonomie: ACTIVA\n"
            "  Filtru economic: ACTIV\n\n"
        )
        f.write(separator)

        f.write("REZUMAT PE VARIANTE\n\n")
        for _, row in df_ablation_summary.iterrows():
            f.write(
                f"{row['varianta']}\n"
                f"  Scenarii: {int(row['nr_scenarii'])}\n"
                f"  Cost total mediu: {row['cost_total_mediu']:.4f}\n"
                f"  Gain mediu: {row['gain_mediu_proc']:.4f}%\n"
                f"  Gain median: {row['gain_median_proc']:.4f}%\n"
                f"  Gain std: {row['gain_std_proc']:.4f}\n"
                f"  Gain minim: {row['gain_min_proc']:.4f}%\n"
                f"  Gain maxim: {row['gain_max_proc']:.4f}%\n"
                f"  Misiuni drona medii: {row['misiuni_drona_medie']:.4f}\n"
                f"\n"
            )
        f.write(separator)

        f.write("IMPACT MEDIU FATA DE FULL\n\n")
        for _, row in df_impact_mediu.iterrows():
            f.write(
                f"{row['varianta']}\n"
                f"  Delta cost vs FULL: {row['delta_cost_mediu_vs_FULL_km']:.4f}\n"
                f"  Delta gain vs FULL: {row['delta_gain_mediu_vs_FULL_pp']:.4f} puncte procentuale\n"
                f"  Delta misiuni vs FULL: {row['delta_misiuni_medie_vs_FULL']:.4f}\n"
                f"\n"
            )
        f.write(separator)

        f.write(f"Timp total rulare ablation: {timp_total_ablation:.4f} secunde\n")


def afiseaza_rezumat(tabele):
    print("\n--- REZUMAT ABLATION ---")
    for _, row in tabele['Rezumat variante'].iterrows():
        print(
            f"{row['varianta']}: "
            f"gain mediu = {row['gain_mediu_proc']:.2f}% | "
            f"cost mediu = {row['cost_total_mediu']:.2f} | "
            f"misiuni medii = {row['misiuni_drona_medie']:.2f}"
        )

    print("\n--- IMPACT FATA DE FULL ---")
    for _, row in tabele['Impact mediu'].iterrows():
        print(
            f"{row['varianta']}: "
            f"Delta gain = {row['delta_gain_mediu_vs_FULL_pp']:+.2f} pp | "
            f"Delta cost = {row['delta_cost_mediu_vs_FULL_km']:+.2f}"
        )
