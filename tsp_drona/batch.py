"""Rularea in batch a scenariilor (FULL si ablation), cu salvarea output-ului de terminal in fisiere."""

import contextlib
import io
import os
import time

import pandas as pd

from . import config
from .euristica import VARIANTA_FULL, VARIANTE_ABLATION, run_scenario, run_scenario_ablation


def formateaza_SL(valoare):
    # 0 -> "0", 0.5 -> "0.5", 1 -> "1", 1.5 -> "1.5"
    return (
        str(valoare).rstrip('0').rstrip('.')
        if '.' in str(valoare)
        else str(valoare)
    )


def _ruleaza_si_salveaza(cale_fisier, functie, *args):
    """Ruleaza functia capturand output-ul de terminal si il scrie in cale_fisier."""
    buffer_output = io.StringIO()
    with contextlib.redirect_stdout(buffer_output):
        rezultat = functie(*args)

    with open(cale_fisier, 'w', encoding='utf-8') as f:
        f.write(buffer_output.getvalue())

    return rezultat


def ruleaza_full(date, folder_iesire_baza):
    """Ruleaza toate combinatiile (SL=SR, alpha, AD) cu euristica originala.

    Fisierele sunt organizate pe foldere in functie de AD, de ex.
    'Folder 1 - Set 1 - AD10/SL_SR_0.5_alpha_3_AD_10.txt'.
    """
    toate_rezumatele = []
    timp_start_batch = time.perf_counter()

    for AD in config.VALORI_AD:
        cale_folder = os.path.join(folder_iesire_baza, config.FOLDERE_AD[AD])
        os.makedirs(cale_folder, exist_ok=True)

        for alpha in config.VALORI_ALPHA:
            for SL_SR in config.VALORI_SL_SR:
                SL = SR = SL_SR

                nume_fisier = f"SL_SR_{formateaza_SL(SL_SR)}_alpha_{alpha}_AD_{AD}.txt"
                cale_fisier = os.path.join(cale_folder, nume_fisier)

                rezumat = _ruleaza_si_salveaza(cale_fisier, run_scenario, date, SL, SR, alpha, AD)
                toate_rezumatele.append(rezumat)

                print(
                    f"[OK] "
                    f"AD={AD} "
                    f"alpha={alpha} "
                    f"SL=SR={SL_SR}  "
                    f"(timp: "
                    f"{rezumat['timp_executie_sec']:.4f}s)  "
                    f"->  "
                    f"{cale_fisier}"
                )

    timp_total_batch_sec = time.perf_counter() - timp_start_batch

    # Tabel comparativ cu toate scenariile
    cale_rezumat = os.path.join(folder_iesire_baza, "rezumat_toate_scenariile.xlsx")
    pd.DataFrame(toate_rezumatele).to_excel(cale_rezumat, index=False)

    print(f"\nGata! Toate cele {len(toate_rezumatele)} scenarii au fost rulate.")
    print(f"Fisierele individuale sunt in subfolderele din: {folder_iesire_baza}")
    print(f"Tabelul comparativ este in: {cale_rezumat}")
    print(
        f"\nTimp total executie batch "
        f"({len(toate_rezumatele)} scenarii): "
        f"{timp_total_batch_sec:.2f} secunde "
        f"({timp_total_batch_sec/60:.2f} minute)"
    )
    print(f"Timp mediu per scenariu: {timp_total_batch_sec/len(toate_rezumatele):.4f} secunde")

    return toate_rezumatele


def ruleaza_ablation(date, folder_ablation, toate_rezumatele):
    """Ruleaza cele 3 variante de ablation pentru fiecare configuratie.

    FULL NU este rulat prin run_scenario_ablation(): este copiat DIRECT din
    rezultatele obtinute de run_scenario() ORIGINAL.
    Tabel final: 36 FULL + 36 x 3 ablation = 144 randuri.
    """
    os.makedirs(folder_ablation, exist_ok=True)

    rezultate_ablation = [
        {'varianta': VARIANTA_FULL, **rezultat_original}
        for rezultat_original in toate_rezumatele
    ]

    timp_start_ablation = time.perf_counter()

    for AD in config.VALORI_AD:
        folder_AD_ablation = os.path.join(folder_ablation, f"AD{AD}")
        os.makedirs(folder_AD_ablation, exist_ok=True)

        for alpha in config.VALORI_ALPHA:
            for SL_SR in config.VALORI_SL_SR:
                SL = SR = SL_SR

                for varianta in VARIANTE_ABLATION:
                    nume_fisier = (
                        f"{varianta}_SL_SR_{formateaza_SL(SL_SR)}_alpha_{alpha}_AD_{AD}.txt"
                    )
                    cale_fisier = os.path.join(folder_AD_ablation, nume_fisier)

                    rezultat = _ruleaza_si_salveaza(
                        cale_fisier, run_scenario_ablation, date, SL, SR, alpha, AD, varianta
                    )
                    rezultate_ablation.append(rezultat)

                    print(
                        f"[ABLATION OK] "
                        f"{varianta} | "
                        f"AD={AD} | "
                        f"alpha={alpha} | "
                        f"SL=SR={SL_SR} | "
                        f"gain="
                        f"{rezultat['economie_procent']:.2f}%"
                    )

    timp_total_ablation = time.perf_counter() - timp_start_ablation

    return rezultate_ablation, timp_total_ablation
