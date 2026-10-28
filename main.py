"""Rulare completa: cele 36 de scenarii FULL + ablation study (108 rulari).

Utilizare:
    python main.py                      # rezultatele in ./rezultate
    python main.py --output D:\\Rezultate
    python main.py --fara-ablation      # doar cele 36 de scenarii FULL
"""

import argparse
import os
import sys

from tsp_drona import config
from tsp_drona.analiza import afiseaza_rezumat, construieste_tabele, exporta_excel, scrie_raport_txt
from tsp_drona.batch import ruleaza_ablation, ruleaza_full
from tsp_drona.date import incarca_date
from tsp_drona.euristica import VARIANTE_ABLATION


def main():
    parser = argparse.ArgumentParser(description="Euristica camion + drona: batch + ablation study")
    parser.add_argument(
        "--output", default=str(config.FOLDER_IESIRE_IMPLICIT),
        help="folderul in care se scriu rezultatele (implicit: ./rezultate)",
    )
    parser.add_argument(
        "--fara-ablation", action="store_true",
        help="ruleaza doar cele 36 de scenarii FULL, fara ablation study",
    )
    args = parser.parse_args()

    # Consola Windows nu afiseaza implicit diacriticele / caracterele UTF-8
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    folder_iesire_baza = args.output
    os.makedirs(folder_iesire_baza, exist_ok=True)

    date = incarca_date()

    # 1. Scenariile FULL (euristica originala)
    toate_rezumatele = ruleaza_full(date, folder_iesire_baza)

    if args.fara_ablation:
        print("\nGATA.")
        return

    # 2. Ablation study
    folder_ablation = os.path.join(folder_iesire_baza, "Ablation Study")
    rezultate_ablation, timp_total_ablation = ruleaza_ablation(
        date, folder_ablation, toate_rezumatele
    )

    tabele = construieste_tabele(rezultate_ablation)

    cale_excel_ablation = os.path.join(folder_ablation, "ablation_study.xlsx")
    exporta_excel(tabele, cale_excel_ablation)

    cale_raport_ablation = os.path.join(folder_ablation, "rezumat_ablation.txt")
    scrie_raport_txt(tabele, cale_raport_ablation, timp_total_ablation)

    nr_configuratii = len(config.VALORI_AD) * len(config.VALORI_ALPHA) * len(config.VALORI_SL_SR)

    print("\n")
    print("=" * 80)
    print("ABLATION STUDY FINALIZAT")
    print("=" * 80)
    print(
        "\nLogica algoritmica FULL nu a fost modificata; "
        "au fost adaugate doar doua statistici de raportare."
    )
    print(f"\nRezultate FULL originale: {len(toate_rezumatele)}")
    print(f"Rulari experimentale ablation: {len(VARIANTE_ABLATION) * nr_configuratii}")
    print(f"Total randuri in tabelul ablation: {len(tabele['Toate rezultatele'])}")
    print(f"\nTimp total ablation: {timp_total_ablation:.2f} secunde")
    print(f"\nFisier Excel ablation:\n{cale_excel_ablation}")
    print(f"\nRaport TXT ablation:\n{cale_raport_ablation}")
    print(f"\nOutput-urile individuale sunt in:\n{folder_ablation}")

    afiseaza_rezumat(tabele)

    print("\nGATA.")


if __name__ == "__main__":
    main()
