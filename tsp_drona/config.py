"""Configurare: cai catre fisierele de date, folderul de iesire si parametrii experimentului."""

from pathlib import Path

# Radacina proiectului (folderul care contine main.py)
ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
CALE_MATRICE = DATA_DIR / "matrice_distante.xlsx"
CALE_ORASE = DATA_DIR / "Orase.xlsx"
CALE_TSP = DATA_DIR / "ruta_optima_tsp.txt"

# Unde se vor crea "Folder 1 - Set 1 - AD10" etc. (poate fi schimbat din linia de comanda)
FOLDER_IESIRE_IMPLICIT = ROOT / "rezultate"

MAX_DRONE_PAYLOAD_KG = 3  # ramane constant in toate scenariile

DEPOZIT_IDX = 1
SEED_CERERI = 42

# Combinatiile de parametri
VALORI_SL_SR = [0, 0.5, 1, 1.5]
VALORI_ALPHA = [2, 3, 4]
VALORI_AD = [10, 20, 30]

# Denumirea folderului pentru fiecare valoare AD
FOLDERE_AD = {
    10: "Folder 1 - Set 1 - AD10",
    20: "Folder 2 - Set 2 - AD20",
    30: "Folder 3 - Set 3 - AD30",
}
