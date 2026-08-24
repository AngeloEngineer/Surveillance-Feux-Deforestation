import os
import requests
from dotenv import load_dotenv

load_dotenv()

MAP_KEY = os.getenv("FIRMS_MAP_KEY")
SOURCE = "VIIRS_SNPP_NRT"                       # Résolution 375 m, meilleure que MODIS (1 Km) pour les feux de brousse souvent petits
AREA = "-0.144,5.927,1.809,11.140" # west,south,east,north — bounding box Togo, conforme au scope réduit décidé (contrainte disque)
DAY_RANGE = 5  # maximum autorisé par l'API

url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAY_RANGE}"

response = requests.get(url)
response.raise_for_status()
lines = response.text.strip().split("\n")
print(f"Statut HTTP : {response.status_code}")
print(f"Lignes reçues : {len(lines)}")
print("En-tête :", lines[0])
if len(lines) >1:
    print("Premier enregistrement :", lines[1])
else:
    print("Aucune détection sur cette fenêtre — normal si aucun feu actif au Togo aujourd'hui.")