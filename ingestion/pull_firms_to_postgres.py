import os
import csv
import io
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

#Définition des variables clés et voir leur définition dans scripts/test_firms_connection
MAP_KEY = os.getenv("FIRMS_MAP_KEY")
SOURCE = "VIIRS_SNPP_NRT"
AREA = "-0.144,5.927,1.809,11.140" # west,south,east,north — bounding box Togo, conforme au scope réduit décidé (contrainte disque)
DAY_RANGE = 5

PG_DSN = (
    f"host=localhost port=5433 dbname=surveillance "
    f"user=surveillance password={os.getenv("POSTGRES_PASSWORD")}"
)

def fetch_detections():
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAY_RANGE}"
    response = requests.get(url)
    response.raise_for_status()
    return list(csv.DictReader(io.StringIO(response.text)))

def insert_detections(rows):
    if not rows:
        print("Aucune détection reçue.")
        return 0
    conn = psycopg2.connect(PG_DSN)
    cur = conn.cursor()
    inserted = 0
    for row in rows:
        row["latitude"] = float(row["latitude"])
        row["longitude"] = float(row["longitude"])
        row["bright_ti4"] = float(row["bright_ti4"]) if row["bright_ti4"] else None
        row["scan"] = float(row["scan"]) if row["scan"] else None
        row["track"] = float(row["track"]) if row["track"] else None
        row["bright_ti5"] = float(row["bright_ti5"]) if row["bright_ti5"] else None
        row["frp"] = float(row["frp"]) if row["frp"] else None
        cur.execute(
            """
            INSERT INTO fire_detections (
                geom, latitude, longitude, bright_ti4, scan, track,
                acq_date, acq_time, satellite, instrument, confidence,
                version, bright_ti5, frp, daynight
            ) VALUES (
                ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326),
                %(latitude)s, %(longitude)s, %(bright_ti4)s, %(scan)s, %(track)s,
                %(acq_date)s, %(acq_time)s, %(satellite)s, %(instrument)s, %(confidence)s,
                %(version)s, %(bright_ti5)s, %(frp)s, %(daynight)s
            )
            ON CONFLICT (latitude, longitude, acq_date, acq_time, satellite) DO NOTHING
            """,
            row,
        )
        inserted += cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return inserted

if __name__ == "__main__":
    rows = fetch_detections()
    print(f"Détections recues de FIRMS: {len(rows)}")
    print(f"Nouvelles lignes insérées: {insert_detections(rows)}")