# Documentation technique — Système de surveillance des feux de brousse et de la déforestation

---

## Table des matières

1. [Introduction](#1-introduction)
2. [Objectif du projet](#2-objectif-du-projet)
3. [Environnement matériel et logiciel](#3-environnement-matériel-et-logiciel)
4. [Chronologie des étapes réalisées](#4-chronologie-des-étapes-réalisées)
   - [Étape 0 — Audit des ressources Docker](#étape-0--audit-des-ressources-docker)
   - [Étape 1 — Initialisation du dépôt Git](#étape-1--initialisation-du-dépôt-git)
   - [Étape 2/3 — Scaffold README et premier commit](#étape-23--scaffold-readme-et-premier-commit)
   - [Étape 4 — Mise en place du .gitignore](#étape-4--mise-en-place-du-gitignore)
   - [Étape 5 — Remplacement des journaux par documentation.md](#étape-5--remplacement-des-journaux-par-documentationmd)
   - [Étape 6 — Obtention de la clé NASA FIRMS et configuration des secrets](#étape-6--obtention-de-la-clé-nasa-firms-et-configuration-des-secrets)
   - [Étape 7 — Environnement virtuel Python et dépendances minimales](#étape-7--environnement-virtuel-python-et-dépendances-minimales)
   - [Étape 8 — Premier test de l'API FIRMS et découvre de la vraie limite day_range](#étape-8--premier-test-de-lapi-firms-et-découverte-de-la-vraie-limite-day_range)
   - [Étape 9 — Déploiement PostgreSQL/PostGIS et résolution du problème .env/docker-compose](#étape-9--déploiement-postgresqlpostgis-et-résolution-du-problème-envdocker-compose)
   - [Étape 10 — Script d'ingestion FIRMS → PostgreSQL](#étape-10--script-dingestion-firms--postgresql)
   - [Étape 14 — Instrumentation temps fetch/insert](#étape-14--instrumentation-temps-fetchinsert)
   - [Étape 17 — Constat volumétrie/temps mono-nœud](#étape-17--constat-volumétrietemps-mono-nœud)
5. [État actuel du code](#5-état-actuel-du-code)
6. [Historique Git](#6-historique-git)
7. [Décisions techniques](#7-décisions-techniques)
8. [Blocages rencontrés](#8-blocages-rencontrés)
9. [Structure actuelle du dépôt](#9-structure-actuelle-du-dépôt)
10. [Reproduction depuis zéro](#10-reproduction-depuis-zéro)
11. [Informations manquantes](#11-informations-manquantes)
12. [Glossaire](#12-glossaire)
13. [Checklist de validation](#13-checklist-de-validation)

---

## 1. Introduction

Ce document est le manuel de reproduction intégrale du projet de surveillance des feux de brousse et de la déforestation. Il a pour objectif de permettre à une personne extérieure au projet de reproduire l'intégralité des étapes réalisées, de comprendre les choix techniques effectués, et de continuer le développement sans avoir besoin de contacter l'auteur.

Ce document suit une chronologie factuelle : chaque étape est documentée dans l'ordre chronologique de sa réalisation, avec les commandes exactes exécutées, les résultats obtenus, et les justifications des choix effectués.

**Règle de lecture :** Ce document ne contient que des faits vérifiés. Lorsqu'une information est inconnue, elle est explicitement signalée par le badge ⚠️ INFORMATION MANQUANTE.

---

## 2. Objectif du projet

### Problème traité

Le système vise à détecter et suivre les feux de brousse et la déforestation en Afrique de l'Ouest. Les feux de brousse dans cette région ont une double origine :

1. **Pratiques agricoles volontaires (brûlis)** — technique agricole traditionnelle de préparation des terres
2. **Incendies incontrôlés** — feux accidentels ou criminels échappant à tout contrôle

Le système doit permettre de distinguer ces deux origines pour permettre aux gestionnaires forestiers et services agricoles d'agir tôt plutôt que de constater les dégâts après coup.

### Utilisateurs visés

| Utilisateur | Rôle dans le système |
|-------------|---------------------|
| Gestionnaires d'aires protégées | Réceptionner les alertes de feux dans leurs zones de responsabilité |
| Services forestiers | Suivre l'évolution de la déforestation et planifier les interventions |
| Acteurs agricoles locaux | Recevoir des informations sur les risques d'incendie dans leurs zones d'activité |

### Sous-problèmes techniques identifiés

| Problème | Description |
|----------|-------------|
| Hétérogénéité de vélocité | Les sources de données ont des rythmes très différents : détections de feux quasi continues, alertes de déforestation hebdomadaires, imagerie satellite ponctuelle |
| Jointures spatiales | Points de détection croisés avec des polygones administratifs/aires protégées — une jointure spatiale naïve devient impraticable au-delà d'un certain volume |
| Faux positifs | Torchères de gaz, activité industrielle détectées à tort comme feux |
| Couverture nuageuse | Les capteurs optiques sont aveuglés en saison des pluies, nécessitant une source radar en complément |

### Approche délibérée

La frontière entre le cœur Big Data distribué (données ponctuelles/vectorielles) et le traitement d'imagerie satellite est volontairement tracée : l'imagerie satellite est traitée comme un outil de vérification ciblé, hors du flux distribué principal.

---

## 3. Environnement matériel et logiciel

### Système d'exploitation

| Paramètre | Valeur |
|-----------|--------|
| OS | Linux |
| Distribution | Pop!_OS (base Ubuntu) |
| Type | Installation native (pas de couche WSL2 ni de virtualisation) |

### Ressources matérielles

| Ressource | Valeur mesurée | Impact sur l'architecture |
|-----------|---------------|--------------------------|
| CPU | 8 cœurs logiques (4 physiques + hyperthreading) | Contrainte secondaire par rapport à la RAM ; limite le nombre d'exécuteurs Spark parallèles |
| RAM système | 16 Go | Détermine l'allocation Docker |
| Espace disque | < 50 Go disponible | Facteur de réplication HDFS réduit à 2 (au lieu de 3 par défaut) |

### Environnement Docker

| Paramètre | Valeur initiale | Valeur après correction | Impact |
|-----------|----------------|------------------------|--------|
| Mémoire allouée | 5.784 GiB | 10.2 GiB | 5.78 GiB insuffisant pour HDFS + Kafka + Spark + PostgreSQL simultanés |

### Environnement partagé — État réel des conteneurs

Docker est partagé avec d'autres systèmes déjà en production locale. Voici l'état réel au moment de la documentation :

| Conteneur | Statut | Port(s) | Projet d'origine |
|-----------|--------|---------|-----------------|
| `surveillance_postgres` | Up | `5433:5432` | Ce projet |
| `veille_prix_postgres` | Up | `5434:5432` | Pipeline de veille des prix agricoles |
| `veille_prix_mongo` | Up | `27018:27017` | Pipeline de veille des prix agricoles |
| `sikapay_metabase` | Up | `3000:3000` | Instance de visualisation |
| `airflow-airflow-apiserver-1` | Up (healthy) | `8080:8080` | Instance Airflow |
| `airflow-airflow-dag-processor-1` | Up (healthy) | — | Instance Airflow |
| `airflow-airflow-scheduler-1` | Up (starting) | — | Instance Airflow |
| `airflow-airflow-triggerer-1` | Up (healthy) | — | Instance Airflow |
| `airflow-airflow-worker-1` | Up (starting) | — | Instance Airflow |
| `airflow-postgres-1` | Up (healthy) | — | Instance Airflow |

### Points de vigilance — Conflits de ports

| Port | Service actuel | Service futur en conflit | Solution retenue |
|------|---------------|-------------------------|------------------|
| 8080 | airflow-airflow-apiserver-1 (interface web Airflow) | Spark (interface web par défaut) | Remapping explicite : `8081:8080` pour Spark |
| 5433 | surveillance_postgres (ce projet) | — | Déjà mappé en `5433:5432` pour éviter le conflit avec PostgreSQL système |

### Logiciels installés

| Logiciel | Version | Rôle dans le projet |
|----------|---------|---------------------|
| Docker | Non vérifié (⚠️ INFORMATION MANQUANTE) | Conteneurisation de l'ensemble du cluster |
| Docker Desktop | Non vérifié (⚠️ INFORMATION MANQUANTE) | Interface graphique de gestion Docker |
| Git | Non vérifié (⚠️ INFORMATION MANQUANTE) | Versioning du code source |
| Java | OpenJDK 17.0.19 | Runtime Java pour Hadoop/Spark |
| Python | 3.x (⚠️ INFORMATION MANQUANTE : version exacte non vérifiée) | Scripts d'ingestion et de test |

### Environnement Python

| Composant | État | Vérification |
|-----------|------|-------------|
| `.venv/` | Créé et fonctionnel | `.venv/bin/python` pointe vers python3 |
| `requests` | Installé (v2.34.2) | `pip list` |
| `python-dotenv` | Installé (v1.2.3) | `pip list` |
| `psycopg2-binary` | Installé (v2.9.12) | `pip list` — dépendance pour PostgreSQL |
| `requirements.txt` | Généré via `pip freeze` | 7 lignes, verrouillé |

---

## 4. Chronologie des étapes réalisées

---

### Étape 0 — Audit des ressources Docker

**Objectif**

Vérifier les ressources réellement disponibles pour Docker avant tout dimensionnement d'architecture.

**Prérequis**

- Docker installé et démarré
- Accès en ligne de commande

**Actions**

1. Exécuter la commande d'audit :

```bash
docker info | grep -E "CPUs|Total Memory"
```

2. Résultat initial :

```
CPUs: 8
Total Memory: 5.784GiB
```

3. Analyse : 5.78 GiB insuffisant pour HDFS + Kafka + Spark + PostgreSQL simultanés.

4. Augmentation manuelle via Docker Desktop : Settings > Resources > Memory > 10 GiB > Apply & Restart.

5. Vérification après redémarrage :

```bash
docker info | grep -E "CPUs|Total Memory"
# CPUs: 8
# Total Memory: 10.2GiB
```

6. Audit de l'environnement partagé :

```bash
docker ps
# Conteneurs actifs : veille_prix_postgres, veille_prix_mongo, sikapay_metabase, airflow-*
```

```bash
docker stats --no-stream
# ~1.3 Gio utilisés sur 10.2 GiB, ~8.9 Gio disponibles
```

**Résultat**

| Métrique | Avant | Après |
|----------|-------|-------|
| RAM Docker | 5.784 GiB | 10.2 GiB |
| RAM disponible pour le projet | — | ~8.9 GiB |

**Critère de passage**

`docker info | grep "Total Memory"` affiche `10.2GiB`.

---

### Étape 1 — Initialisation du dépôt Git

**Objectif**

Créer le répertoire du projet et initialiser un dépôt Git.

**Actions**

```bash
mkdir ~/Mes_Projets/surveillance-feux-deforestation
cd ~/Mes_Projets/surveillance-feux-deforestation
git init
git branch -m main
```

**Résultat**

- Répertoire créé
- Dépôt Git initialisé
- Branche renommée de `master` à `main`

**Critère de passage**

`git branch` affiche `* main`.

---

### Étape 2/3 — Scaffold README et premier commit

**Objectif**

Créer la structure initiale du projet avec un fichier README.md.

**Actions**

```bash
mkdir docs
touch docs/decisions.md
touch docs/blocages.md
# Création du README.md (contenu initial)
git add README.md docs/
git commit -m "Initialise la structure du projet et la documentation de cadrage"
```

**Résultat**

- Premier commit enregistré
- Hash : `48f4a3a`

---

### Étape 4 — Mise en place du .gitignore

**Objectif**

Empêcher le commit accidentel de secrets et de fichiers volumineux.

**Actions**

```bash
# Création du .gitignore
git add .gitignore
git commit -m "Ajoute le fichier .gitignore"
```

**Contenu du .gitignore (version initiale)**

```
# Python
__pycache__/
*.pyc
.venv/
venv/
*.egg-info/
.pytest_cache/
.mypy_cache/

# Secrets
.env
.env.*
*.key
secrets/

# Données volumineuses
data/raw/
data/interim/
*.tif
*.tiff
*.parquet
*.nc

# Docker
docker/volumes/

# OS / éditeur
.DS_Store
Thumbs.db

# Logs
*.log
```

**Push vers GitHub**

```bash
git push
# Erreur : fatal: Pas de destination pour pousser.

git remote add origin https://github.com/AngeloEngineer/Surveillance-Feux-Deforestation.git
git push -u origin main
# Succès — branche main poussée vers GitHub
```

**Résultat**

- Deuxième commit enregistré
- Hash : `895cdff`
- Dépôt distant GitHub configuré

---

### Étape 5 — Remplacement des journaux par documentation.md

**Objectif**

Remplacer `docs/decisions.md` et `docs/blocages.md` par un fichier unique `docs/documentation.md`.

**Décision**

Un document narratif unique, intégrant décisions et blocages en contexte, est plus utile pour la reproductibilité qu'une série de tableaux déconnectés du raisonnement.

**Actions**

```bash
git rm docs/decisions.md docs/blocages.md
touch docs/documentation.md
git add docs/
git commit -m "Remplace les journaux décisions/blocages par une documentation complète"
git push
```

**Résultat**

- Troisième commit enregistré
- Hash : `4817ffe`

---

### Étape 6 — Obtention de la clé NASA FIRMS et configuration des secrets

**Objectif**

Obtenir la clé d'accès API (MAP_KEY) auprès de NASA FIRMS, puis sécuriser le dépôt contre la divulgation de cette clé.

**Actions**

1. **Demande de la clé :** Se rendre sur https://firms.modaps.eosdis.nasa.gov/api/map_key, renseigner son email. La clé est envoyée par email.

2. **Modification du `.gitignore` :** Suppression de la ligne `.env.*` (empêchait la prise en compte de `.env.example`).

3. **Création de `.env.example` :**

```
# Documente la forme de ton vrai fichier .env
FIRMS_MAP_KEY=
# Mot de passe PostGis qui sera utilisé dans docker/docker-compose.yml
POSTGRES_PASSWORD=
```

4. **Création de `.env` (non versionné) :** Contient `FIRMS_MAP_KEY=<clé>` et `POSTGRES_PASSWORD=<mot_de_passe>`.

```bash
git add .gitignore .env.example
git commit -m "Ajout du fichier .env.example et mise à jour du gitignore"
git push
```

**Résultat**

- Quatrième commit enregistré
- Hash : `dcf7048`

---

### Étape 7 — Environnement virtuel Python et dépendances minimales

**Objectif**

Créer un environnement virtuel Python isolé et installer les dépendances nécessaires à l'ingestion de données FIRMS.

**Pourquoi seulement ces dépendances**

| Dépendance | Rôle | Pourquoi elle est nécessaire |
|------------|------|------------------------------|
| `requests` | Client HTTP | Appels à l'API REST de NASA FIRMS |
| `python-dotenv` | Chargement de variables d'environnement | Lire `FIRMS_MAP_KEY` depuis `.env` sans l'écrire en dur |
| `psycopg2-binary` | Client PostgreSQL | Connexion à la base PostgreSQL/PostGIS pour l'insertion des données |

**Actions**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests python-dotenv psycopg2-binary
pip freeze > requirements.txt
```

**Vérification**

```bash
python -c "import requests, dotenv, psycopg2; print('ok')"
# ok

pip list
# certifi            2026.7.22
# charset-normalizer 3.5.1
# idna               3.19
# psycopg2-binary    2.9.12
# python-dotenv      1.2.3
# requests           2.34.2
# urllib3            2.7.0
```

**`requirements.txt` généré (7 lignes)**

```
certifi==2026.7.22
charset-normalizer==3.5.1
idna==3.19
psycopg2-binary==2.9.12
python-dotenv==1.2.3
requests==2.34.2
urllib3==2.7.0
```

**Critère de passage**

- [ ] `.venv/` existe et contient un Python fonctionnel
- [ ] `requirements.txt` contient `requests`, `python-dotenv` et `psycopg2-binary`
- [ ] `python -c "import requests, dotenv, psycopg2; print('ok')"` affiche `ok`

---

### Étape 8 — Premier test de l'API FIRMS et découverte de la vraie limite day_range

**Objectif**

Valider que la clé MAP fonctionne en interrogeant l'API FIRMS avec un script minimal, puis identifier la limite réelle du paramètre `day_range`.

**Prérequis**

- Environnement virtuel Python actif (Étape 7)
- Fichier `.env` contenant `FIRMS_MAP_KEY` (Étape 6)

**Script de test : `scripts/test_firms_connection.py`**

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()

MAP_KEY = os.getenv("FIRMS_MAP_KEY")
SOURCE = "VIIRS_SNPP_NRT"
AREA = "-0.144,5.927,1.809,11.140"  # west,south,east,north — bounding box Togo
DAY_RANGE = 5  # maximum autorisé par l'API

url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAY_RANGE}"

response = requests.get(url)
response.raise_for_status()
lines = response.text.strip().split("\n")
print(f"Statut HTTP : {response.status_code}")
print(f"Lignes reçues : {len(lines)}")
print("En-tête :", lines[0])
if len(lines) > 1:
    print("Premier enregistrement :", lines[1])
else:
    print("Aucune détection — normal si aucun feu actif au Togo aujourd'hui.")
```

**Problème rencontré — limite day_range non conforme à la documentation**

| Test `day_range` | Statut HTTP | Résultat |
|------------------|-------------|----------|
| 1 | 200 | Succès (0 détection — saison des pluies) |
| 2 | 200 | Succès |
| 3 | 200 | Succès |
| 5 | 200 | Succès |
| 7 | 400 | Échec |
| 10 | 400 | Échec |

**Message d'erreur pour `day_range=7` :** `"Invalid day range. Expects [1..5]."`

**Cause réelle :** La documentation publique NASA FIRMS annonce une plage de 1-10, mais la vraie limite appliquée est **1-5**.

**Décision :** `DAY_RANGE` fixé à **5** dans tous les scripts.

**Leçon retenue :** Ne jamais faire confiance à une documentation externe sans la valider empiriquement. En cas d'erreur peu explicite (HTTP 400 sans détail), tester par bisection.

---

### Étape 9 — Déploiement PostgreSQL/PostGIS et résolution du problème .env/docker-compose

**Objectif**

Mettre en place un conteneur PostgreSQL/PostGIS comme baseline classique du Niveau 2.

**Fichier `docker/docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgis/postgis:16-3.4
    container_name: surveillance_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: surveillance
      POSTGRES_USER: surveillance
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    mem_limit: 512m

volumes:
  postgres_data:
```

**Problème rencontré — Docker Compose ignore le fichier .env**

```bash
docker compose -f docker/docker-compose.yml up -d
# Avertissement : The POSTGRES_PASSWORD variable is not set. Defaulting to a blank string.
```

**Cause :** Docker Compose ne lit un `.env` que s'il est dans le même dossier que le fichier compose. Ici, `.env` est à la racine, `docker-compose.yml` est dans `docker/`.

**Complication :** PostgreSQL n'applique `POSTGRES_PASSWORD` qu'à la première initialisation du volume. Le volume avait déjà été créé avec un mot de passe vide.

**Contournement appliqué :**

```bash
docker compose -f docker/docker-compose.yml down -v
docker compose --env-file .env -f docker/docker-compose.yml up -d
```

**Vérification :**

```bash
docker exec surveillance_postgres psql -U surveillance -c "SELECT version();"
# PostgreSQL 16.4 (Debian 16.4-1.pgdg110+2) on x86_64-pc-linux-gnu
```

**État actuel du conteneur :**

| Paramètre | Valeur |
|-----------|--------|
| Nom | `surveillance_postgres` |
| Statut | Up (5+ heures) |
| Image | `postgis/postgis:16-3.4` |
| Port | `5433:5432` |
| Base de données | `surveillance` |
| Utilisateur | `surveillance` |
| PostgreSQL | 16.4 confirmé |
| Mémoire | 512 Mo max |

---

### Étape 10 — Script d'ingestion FIRMS → PostgreSQL

**Objectif**

Créer un script qui récupère les détections de feux depuis l'API FIRMS et les insère dans PostgreSQL/PostGIS.

**Script : `ingestion/pull_firms_to_postgres.py`**

```python
import os
import csv
import io
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()

MAP_KEY = os.getenv("FIRMS_MAP_KEY")
SOURCE = "VIIRS_SNPP_NRT"
AREA = "-0.144,5.927,1.809,11.140"  # west,south,east,north — bounding box Togo
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
```

**Points clés du script :**

| Fonctionnalité | Détail |
|----------------|--------|
| Source de données | API FIRMS, capteur VIIRS_SNPP_NRT (résolution 375m) |
| Zone géographique | Bounding box du Togo : `-0.144,5.927,1.809,11.140` |
| Fenêtre temporelle | 5 jours (maximum réel de l'API) |
| Connexion PostgreSQL | `localhost:5433`, base `surveillance`, utilisateur `surveillance` |
| Insertion | `ON CONFLICT DO NOTHING` — pas de doublons |
| Géométrie | `ST_SetSRID(ST_MakePoint(lon, lat), 4326)` — point en WGS84 |

**Script de test : `scripts/test_firms_connection.py`**

Script plus simple, sans PostgreSQL, servant uniquement à vérifier que l'API FIRMS répond correctement.

**Schéma de la table cible : `storage/sql/001_create_fire_detections.sql`**

```sql
CREATE TABLE IF NOT EXISTS fire_detections (
    id BIGSERIAL PRIMARY KEY,
    geom GEOMETRY(Point, 4326) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    bright_ti4 DOUBLE PRECISION,
    scan DOUBLE PRECISION,
    track DOUBLE PRECISION,
    acq_date DATE NOT NULL,
    acq_time TEXT NOT NULL,
    satellite TEXT,
    instrument TEXT,
    confidence TEXT,
    version TEXT,
    bright_ti5 DOUBLE PRECISION,
    frp DOUBLE PRECISION,
    daynight CHAR(1),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (latitude, longitude, acq_date, acq_time, satellite)
);

CREATE INDEX IF NOT EXISTS idx_fire_detections_geom ON fire_detections USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_fire_detections_acq_date ON fire_detections (acq_date);
```

**Points clés du schéma :**

| Élément | Détail |
|---------|--------|
| Table | `fire_detections` |
| Clé primaire | `id BIGSERIAL` |
| Géométrie | `geom GEOMETRY(Point, 4326)` — point en WGS84 |
| Index spatial | `GIST (geom)` — pour les jointures spatiales |
| Index temporel | `acq_date` — pour les requêtes par date |
| Contrainte `UNIQUE` | `(latitude, longitude, acq_date, acq_time, satellite)` — évite les doublons |
| Horodatage | `ingested_at TIMESTAMPTZ DEFAULT now()` — moment de l'insertion |

**Justification de la contrainte UNIQUE :** L'API FIRMS renvoie "les N derniers jours depuis aujourd'hui" — des appels répétés du pipeline vont mécaniquement se chevaucher sur les mêmes détections. La contrainte UNIQUE combinée à `ON CONFLICT DO NOTHING` prévient les doublons.

**Exécution du schéma SQL :** Réussie. Vérification :

```bash
docker exec surveillance_postgres psql -U surveillance -c "\d fire_detections"
```

> La table `fire_detections` existe avec 17 colonnes, 4 index (PK, UNIQUE, GIST sur geom, btree sur acq_date).

**Bug 1 — Connexion PostgreSQL échoue avec "password authentication failed for user broly"**

| Élément | Détail |
|---------|--------|
| Symptôme | `psycopg2.OperationalError` — mot de passe chargé depuis `.env` était correct (vérifié avec `repr()`) |
| Cause réelle | Deux f-strings Python adjacentes dans `PG_DSN`, écrites sans espace entre elles (`"dbname=surveillance"` suivi immédiatement de `"user=surveillance"`), concaténées par Python en `"dbname=surveillanceuser=surveillance"`. Le parseur de psycopg2 n'a pas reconnu `"user="` comme clé valide, et la connexion est retombée sur l'utilisateur système (`broly`) par défaut. |
| Diagnostic | Inspection directe du code source (`grep -A3 PG_DSN`) plutôt que supposition |
| Correction | Ajout d'un espace en fin de première ligne de la f-string : `f"host=localhost port=5433 dbname=surveillance "` |
| Leçon | Quand un message d'erreur mentionne une valeur qui ne correspond à aucun paramètre attendu (ici `"broly"` au lieu de `"surveillance"`), le paramètre attendu n'a probablement jamais atteint la librairie — chercher du côté de la construction de la chaîne plutôt que des valeurs elles-mêmes |

**Bug 2 — `psycopg2.errors.UndefinedFunction` sur `ST_SetSRID`**

| Élément | Détail |
|---------|--------|
| Symptôme | Erreur PostgreSQL listant 15 arguments "unknown" passés à `st_setsrid`, alors que la fonction n'en prend normalement que 2 |
| Cause réelle | Parenthèse fermante manquante après `ST_MakePoint(%(longitude)s, %(latitude)s)` — le SRID 4326 était passé comme 3ᵉ argument à `ST_MakePoint` (qui n'accepte que 2 arguments dans cet usage) au lieu d'être l'argument de `ST_SetSRID`. Tous les paramètres suivants de la requête se sont retrouvés aspirés comme arguments supplémentaires. |
| Correction | Ajout de la parenthèse fermante manquante |
| Problème connexe corrigé | `csv.DictReader` renvoie toutes les valeurs en texte, y compris les champs numériques. Cast explicite en `float` (ou `None` si vide) ajouté avant insertion, plutôt que de compter sur une résolution de type implicite côté PostgreSQL |

**Validation de l'idempotence**

| Exécution | Détections reçues | Lignes insérées | Résultat |
|-----------|-------------------|-----------------|----------|
| 1ᵉʳ lancement | 4 | 4 | Données insérées |
| 2ᵉ lancement | 4 (mêmes données) | 0 | Doublons absorbés |

**Conclusion :** La contrainte `UNIQUE` combinée à `ON CONFLICT DO NOTHING` absorbe correctement les doublons issus du chevauchement des fenêtres FIRMS. Le pipeline est idempotent.

---

### Étape 14 — Instrumentation temps fetch/insert

**Objectif**

Établir une baseline chiffrée des performances du pipeline mono-nœud avant élargissement géographique.

**Contexte**

Besoin de mesurer le coût réel de chaque phase (fetch API + insert PostgreSQL) pour identifier les goulets d'étranglement potentiels avant d'élargir la zone géographique.

**Mesure sur bbox Togo (day_range=5)**

| Phase | Temps mesuré | Détail |
|-------|-------------|--------|
| `fetch_detections()` | 2.42 s | Appel HTTP à l'API FIRMS + parsing CSV |
| `insert_detections()` | 0.80 s | Connexion PostgreSQL + 4 INSERT + commit |
| **Total** | **3.22 s** | 4 lignes reçues, 0 insérées (doublons) |

**Constats**

| Observation | Détail |
|-------------|--------|
| Volume insuffisant pour révéler un goulot | 4 lignes ne permettent pas de distinguer l'overhead de connexion du coût réel d'insertion |
| Overhead de connexion domine | La connexion psycopg2 + cur.close() représente une part significative du temps total |
| Insertion ligne par ligne | Chaque `cur.execute()` = 1 aller-retour réseau — pas de batching |

**Prochaine étape :** Élargir la bbox à la sous-région pour obtenir un volume représentatif.

---

### Étape 17 — Constat volumétrie/temps mono-nœud

**Objectif**

Mesurer où le pipeline mono-nœud montre ses limites en élargissant progressivement la bbox.

**Démarche**

Élargissement progressif de la bbox :
1. Togo (bbox initiale)
2. Sous-région (Ghana/Togo/Bénin/Burkina Faso)
3. Afrique de l'Ouest
4. Continent

**Résultats mesurés**

| Zone | Lignes reçues | Débit insert | Temps insert estimé |
|------|---------------|--------------|---------------------|
| Togo (bbox initiale) | 431 | ~1 390 lignes/s | ~0.31 s |
| Sous-région élargie | 261 810 | ~439 lignes/s | ~596 s (~10 min) |

**Observations clés**

| Mesure | Valeur | Interprétation |
|--------|--------|----------------|
| Effondrement du débit | ×3 (1 390 → 439 lignes/s) | Cohérent avec des insertions ligne par ligne sans batching — un aller-retour réseau par `cur.execute()` |
| Volume stocké | 78 MB pour 262 260 lignes | Non limitant à cette échelle |
| Goulot identifié | **Temporel, pas volumétrique** | Le mono-nœud encaisse le volume en stockage mais pas en débit d'écriture |

**Conclusion technique**

Le mono-nœud actuel atteint ses limites de débit d'écriture au rythme visé :
- Fréquence d'ingestion accrue (plusieurs fois par jour)
- Historique qui s'accumule (fenêtre glissante)
- Échelle continentale (plusieurs centaines de milliers de lignes)

> **Justification factuelle pour le Niveau 3 :** Kafka (ingestion distribuée), HDFS (stockage distribué), Spark+Sedona (écriture batch avec parallelisme) — non pas par ambitions technologiques, mais parce que le mono-nœud ne peut plus encaisser le débit requis.

---

## 5. État actuel du code

### Fichiers Python

| Fichier | Rôle | Dépendances | État |
|---------|------|-------------|------|
| `scripts/test_firms_connection.py` | Test de connexion à l'API FIRMS | `requests`, `python-dotenv` | Fonctionnel (testé avec `day_range=5`) |
| `ingestion/pull_firms_to_postgres.py` | Ingestion FIRMS → PostgreSQL | `requests`, `python-dotenv`, `psycopg2-binary` | Fonctionnel — testé, bugs corrigés, idempotence validée |

### Fichiers SQL

| Fichier | Rôle | État |
|---------|------|------|
| `storage/sql/001_create_fire_detections.sql` | Schéma de la table `fire_detections` | Appliqué — table créée et vérifiée avec `\d fire_detections` |

### Fichiers de configuration

| Fichier | Rôle | État |
|---------|------|------|
| `.env` | Variables secrètes (`FIRMS_MAP_KEY`, `POSTGRES_PASSWORD`) | Créé, non versionné |
| `.env.example` | Modèle du `.env` | Créé, versionné (4 lignes) |
| `.gitignore` | Règles d'exclusion Git | Créé, versionné (31 lignes) |
| `requirements.txt` | Dépendances Python verrouillées | Créé, versionné (7 lignes) |
| `docker/docker-compose.yml` | Configuration PostgreSQL/PostGIS | Créé, versionné (17 lignes) |

### Fichiers de log

| Fichier | Contenu | État |
|---------|---------|------|
| `logs/dbt.log` | Log d'exécution de dbt-fusion (license info) | Présent — dbt license expirée (trial) |
| `logs/query_log.sql` | — | Vide (0 lignes) |

> ⚠️ NOTE : La présence de `logs/dbt.log` indique que dbt-fusion a été exécuté sur cette machine. La licence trial est expirée (2026-06-02). Ce n'est pas un blocage pour ce projet à ce stade.

---

## 6. Historique Git

### Branche principale

| Hash court | Message de commit | Étape correspondante |
|------------|-------------------|---------------------|
| `48f4a3a` | Initialise la structure du projet et la documentation de cadrage | Étape 2/3 |
| `895cdff` | Ajoute le fichier .gitignore | Étape 4 |
| `4817ffe` | Remplace les journaux décisions/blocages par une documentation complète | Étape 5 |
| `dcf7048` | Ajout du fichier .env.example et mise à jour du gitignore | Étape 6 |
| `f6bb8c1` | Ajoute et valide le script de test de connexion à l'API FIRMS | Étape 8 |

### Branche active

- Nom : `main`
- La branche est en avance de 1 commit sur `origin/main` (commit `f6bb8c1` non poussé)

### Dépôt distant

| Paramètre | Valeur |
|-----------|--------|
| Nom | `origin` |
| URL | `https://github.com/AngeloEngineer/Surveillance-Feux-Deforestation.git` |
| Branche suivie | `main` |

### Fichiers non suivis (non commités)

| Fichier/Répertoire | Raison |
|--------------------|--------|
| `docker/` | Répertoire non ajouté au staging |
| `ingestion/` | Répertoire non ajouté au staging |
| `logs/` | Répertoire non ajouté au staging |
| `requirements.txt` | Fichier non ajouté au staging |
| `storage/` | Répertoire non ajouté au staging |

> ⚠️ NOTE : Ces fichiers existent localement mais n'ont pas encore été commités. Un `git add . && git commit` sera nécessaire pour les versionner.

---

## 7. Décisions techniques

| # | Décision | Alternatives envisagées | Justification | Étape |
|---|----------|------------------------|---------------|-------|
| D1 | Docker Compose plutôt qu'un cluster physique | — | Seule option réaliste sans infrastructure dédiée | Cadrage initial |
| D2 | Facteur de réplication HDFS = 2 | 3 (valeur par défaut) | Espace disque < 50 Go | Cadrage initial |
| D3 | Mémoire Docker relevée à 10 GiB | Rester à 5.78 GiB | 5.78 GiB insuffisant pour le cluster | Étape 0 |
| D4 | Nom de branche `main` | `master` | Convention standard actuelle | Étape 1 |
| D5 | Documentation unique (documentation.md) | Journaux séparés | Reproductibilité narrative | Étape 5 |
| D6 | Dépôt distant GitHub configuré après push raté | Push immédiat | Le push a échoué — dépôt ajouté manuellement | Étape 4 |
| D7 | Suppression de `.env.*` du `.gitignore` | Garder `.env.*` | Permet de versionner `.env.example` | Étape 6 |
| D8 | Création de `.env.example` avec `FIRMS_MAP_KEY=` et `POSTGRES_PASSWORD=` | Fichier `.env` pré-rempli | Le vrai `.env` ne doit jamais être versionné | Étape 6 |
| D9 | Environnement virtuel `.venv` | Installation globale | Isolation des dépendances | Étape 7 |
| D10 | Seules `requests`, `python-dotenv`, `psycopg2-binary` installées | Ensemble complet | Chaque dépendance ajoutée uniquement quand un besoin réel apparaît | Étape 7 |
| D11 | `requirements.txt` généré via `pip freeze` | Écriture manuelle | Reproductibilité exacte des versions | Étape 7 |
| D12 | `DAY_RANGE=5` pour l'API FIRMS | 10 (valeur documentée) | La vraie limite est 1-5, pas 1-10 | Étape 8 |
| D13 | Image `postgis/postgis:16-3.4` | PostgreSQL standard | PostGIS nécessaire pour les jointures spatiales | Étape 9 |
| D14 | Port PostgreSQL mappé en `5433:5432` | `5432:5432` | Évite le conflit avec PostgreSQL système | Étape 9 |
| D15 | `docker compose --env-file .env` | Lecture implicite | Docker Compose ne lit que le `.env` du même dossier | Étape 9 |
| D16 | `psycopg2-binary` plutôt que SQLAlchemy/ORM | SQLAlchemy, psycopg2 complet | Driver minimal, pas de besoin justifié d'un ORM à ce stade | Étape 10 |
| D17 | Cast explicite en `float` des champs numériques avant insertion | Compter sur la résolution de type implicite PostgreSQL | `csv.DictReader` renvoie tout en texte — PostgreSQL peut rejeter les types | Étape 10 |
| D18 | Instrumentation `time.perf_counter()` ajoutée au pipeline | Pas de mesure des performances | Baseline chiffrée nécessaire avant élargissement géographique | Étape 14 |
| D19 | Élargissement progressif de la bbox (Togo → sous-région → continent) | Élargir directement à l'échelle du continent | Mesurer où le mono-nœud montre ses limites avant de justifier l'architecture distribuée | Étape 17 |

---

## 8. Blocages rencontrés

| # | Blocage | Cause | Contournement | Leçon | Étape |
|---|---------|-------|---------------|-------|-------|
| B1 | Mémoire Docker insuffisante (5.78 GiB) | Configuration antérieure | Relevée à 10 GiB via Docker Desktop | Vérifier `docker info` avant de dimensionner | Étape 0 |
| B2 | Port 8080 en conflit | Airflow occupe ce port | Remapping prévu : `8081:8080` pour Spark | Auditer les ports avant déploiement | Étape 0 |
| B3 | Push Git échoué | Pas de dépôt distant configuré | `git remote add origin` puis `push -u` | Vérifier `git remote -v` avant de pousser | Étape 4 |
| B4 | API FIRMS retourne HTTP 400 avec `day_range=10` | Documentation publique fausse (1-10 au lieu de 1-5) | Bisection empirique, fixation à 5 | Valider empiriquement toute documentation externe | Étape 8 |
| B5 | Docker Compose ignore `.env` | `.env` à la racine, compose dans `docker/` | `--env-file .env` explicitement | Toujours expliciter le chemin du `.env` | Étape 9 |
| B6 | Changement de mot de passe sans effet | PostgreSQL applique `POSTGRES_PASSWORD` seulement à la 1ère init | `down -v` puis relance avec `--env-file` | Un changement de BDD initiale exige de recréer le volume | Étape 9 |
| B7 | `psycopg2` connexion échoue — "user broly" au lieu de "surveillance" | F-strings adjacentes sans espace : `dbname=surveillanceuser=surveillance` | Ajout d'un espace en fin de ligne | Quand l'erreur mentionne une valeur inattendue, le paramètre n'a jamais atteint la librairie — inspecter la construction de la chaîne | Étape 10 |
| B8 | `UndefinedFunction` sur `ST_SetSRID` — 15 arguments "unknown" | Parenthèse fermante manquante après `ST_MakePoint` | Ajout de la parenthèse | Les erreurs de parenthèses dans les requêtes SQL peuvent produire des messages d'erreur trompeurs | Étape 10 |
| B5 | Docker Compose ignore `.env` | `.env` à la racine, compose dans `docker/` | `--env-file .env` explicitement | Toujours expliciter le chemin du `.env` | Étape 9 |
| B6 | Changement de mot de passe sans effet | PostgreSQL applique `POSTGRES_PASSWORD` seulement à la 1ère init | `down -v` puis relance avec `--env-file` | Un changement de BDD initiale exige de recréer le volume | Étape 9 |

---

## 9. Structure actuelle du dépôt

```
surveillance-feux-deforestation/
├── .git/                                    # Dépôt Git
├── .gitignore                               # Règles d'exclusion (31 lignes)
├── .env                                     # Secrets — NON VERSIONNÉ
├── .env.example                             # Modèle du .env (4 lignes, versionné)
├── README.md                                # Description du projet (72 lignes)
├── requirements.txt                         # Dépendances Python verrouillées (7 lignes)
├── .venv/                                   # Environnement virtuel Python — NON VERSIONNÉ
├── docker/
│   └── docker-compose.yml                   # Configuration PostgreSQL/PostGIS (17 lignes)
├── docs/
│   └── documentation.md                     # Ce fichier
├── ingestion/
│   └── pull_firms_to_postgres.py            # Script d'injection FIRMS → PostgreSQL (66 lignes)
├── logs/
│   ├── dbt.log                              # Log dbt-fusion (6 lignes, licence expirée)
│   └── query_log.sql                        # Vide (0 lignes)
├── scripts/
│   └── test_firms_connection.py             # Test de connexion API FIRMS (23 lignes)
└── storage/
    └── sql/
        └── 001_create_fire_detections.sql   # Schéma de la table fire_detections (23 lignes)
```

### Fichiers versionnés (Git)

| Fichier | Lignes | Rôle |
|---------|--------|------|
| `.gitignore` | 31 | Exclut les secrets, données volumineuses, `.venv/` |
| `.env.example` | 4 | Modèle de configuration (`FIRMS_MAP_KEY`, `POSTGRES_PASSWORD`) |
| `README.md` | 72 | Description synthétique du projet |
| `requirements.txt` | 7 | Dépendances Python verrouillées |
| `docker/docker-compose.yml` | 17 | Conteneur PostgreSQL/PostGIS |
| `docs/documentation.md` | Ce fichier | Documentation technique complète |

### Fichiers NON versionnés (existants localement)

| Fichier/Répertoire | Raison |
|--------------------|--------|
| `.env` | Exclu par `.gitignore` — contient des secrets |
| `.venv/` | Exclu par `.gitignore` — environnement virtuel |
| `ingestion/pull_firms_to_postgres.py` | ⚠️ Non encore commité |
| `scripts/test_firms_connection.py` | ⚠️ Non encore commité (le commit `f6bb8c1` concerne un test précédent) |
| `storage/sql/001_create_fire_detections.sql` | ⚠️ Non encore commité |
| `logs/` | ⚠️ Non encore commité |

---

## 10. Reproduction depuis zéro

### Prérequis

| Outil | Version requise | Comment vérifier | Comment installer si absent |
|-------|----------------|------------------|----------------------------|
| Linux | Distribution basée Ubuntu (Pop!_OS recommandé) | `lsb_release -a` | https://pop.system76.com |
| Docker | Dernière version stable | `docker --version` | https://docs.docker.com/engine/install/ubuntu |
| Docker Desktop | Dernière version stable | Icône dans le tray system | https://www.docker.com/products/docker-desktop |
| Git | Dernière version stable | `git --version` | `sudo apt install git` |
| Python 3 | Dernière version stable | `python3 --version` | `sudo apt install python3 python3-venv` |
| Java | OpenJDK 17 | `java --version` | `sudo apt install openjdk-17-jdk` |

### Procédure

1. Installer les prérequis ci-dessus
2. Allouer 10 GiB à Docker (Settings > Resources > Memory)
3. Auditer les ports occupés : `docker ps` — vérifier les ports 8080 et 5433
4. Cloner le dépôt : `git clone https://github.com/AngeloEngineer/Surveillance-Feux-Deforestation.git`
5. Demander la clé MAP_KEY sur https://firms.modaps.eosdis.nasa.gov/api/map_key
6. Créer le fichier `.env` à la racine :
   ```
   FIRMS_MAP_KEY=<clé_reçue>
   POSTGRES_PASSWORD=<mot_de_passe_solide>
   ```
7. Créer l'environnement Python : `python3 -m venv .venv && source .venv/bin/activate`
8. Installer les dépendances : `pip install requests python-dotenv psycopg2-binary && pip freeze > requirements.txt`
9. Vérifier : `python -c "import requests, dotenv, psycopg2; print('ok')"` → `ok`
10. Lancer PostgreSQL : `docker compose --env-file .env -f docker/docker-compose.yml up -d`
11. Vérifier : `docker exec surveillance_postgres psql -U surveillance -c "SELECT version();"` → PostgreSQL 16.4
12. Appliquer le schéma : `docker exec -i surveillance_postgres psql -U surveillance < storage/sql/001_create_fire_detections.sql`
13. Tester l'API : `python scripts/test_firms_connection.py`
14. Lancer l'injection : `python ingestion/pull_firms_to_postgres.py`

---

## 11. Informations manquantes

| Information | Pourquoi elle est nécessaire | Comment la récupérer |
|-------------|----------------------------|---------------------|
| Version exacte de Docker | Compatibilité avec les images | `docker --version` |
| Version exacte de Docker Desktop | Configuration des ressources | Interface Docker Desktop |
| Version exacte de Git | Compatibilité | `git --version` |
| Version exacte de Python | Compatibilité des dépendances | `python3 --version` |
| Espace disque réellement disponible | Dimensionnement du cluster | `df -h /` |

---

## 12. Glossaire

| Terme | Définition | Rôle dans ce projet |
|-------|-----------|---------------------|
| HDFS | Hadoop Distributed File System | Stockage distribué (prévu, pas encore déployé) |
| Kafka | Plateforme de streaming distribué | Ingestion en temps réel (prévu, pas encore déployé) |
| Spark | Moteur de traitement distribué | Traitement et analyse (prévu, pas encore déployé) |
| Docker | Plateforme de conteneurisation | Isolation et déploiement des composants |
| Docker Compose | Outil d'orchestration multi-conteneurs | Définition de l'architecture complète |
| PostgreSQL | Système de gestion de BDD relationnelle | Stockage des données de détection |
| PostGIS | Extension spatiale pour PostgreSQL | Jointures spatiales et requêtes géographiques |
| VIIRS_SNPP_NRT | Capteur satellite résolution 375m, données en temps quasi-réel | Source principale de détection de feux |
| FIRMS | Fire Information for Resource Management System | API NASA de données de détection de feux |
| MAP_KEY | Clé d'API pour accéder à FIRMS | Authentification pour l'ingestion |
| day_range | Paramètre FIRMS — nombre de jours de données | Plage réelle : 1-5 (pas 1-10) |
| bounding box | Rectangle géographique délimitant une zone | Zone d'étude : Togo |
| GeoTIFF | Format d'image satellite géoréférencée | Données d'imagerie (prévu) |
| Parquet | Format de stockage colonnaire optimisé | Données intermédiaires (prévu) |
| NetCDF | Format de données scientifiques multi-dimensionnelles | Données climatiques (prévu) |
| .env | Fichier de configuration locale contenant les secrets | Stocke `FIRMS_MAP_KEY` et `POSTGRES_PASSWORD` |
| .env.example | Modèle du `.env` sans secrets | Référence pour les développeurs |
| dbt | Outil de transformation de données | Log présent mais licence expirée — pas utilisé actuellement |
| psycopg2 | Client PostgreSQL pour Python | Driver minimal pour la connexion à PostgreSQL |
| ON CONFLICT DO NOTHING | Clause SQL d'insertion sans doublon | Empêche les erreurs de duplication lors d'insertions répétées |
| GIST | Generalized Search Tree — type d'index spatial | Permet les requêtes spatiales efficaces (ST_Contains, ST_DWithin) |
| OOMKilled | Processus tué par le système pour manque de mémoire | Risque si l'allocation Docker est insuffisante |

---

## 13. Checklist de validation

### Après l'Étape 0

- [ ] `docker info | grep "Total Memory"` affiche `10.2GiB`
- [ ] `docker ps` montre les conteneurs existants
- [ ] `docker stats --no-stream` confirme ~8.9 Gio disponibles

### Après l'Étape 1

- [ ] Répertoire `~/Mes_Projets/surveillance-feux-deforestation` existe
- [ ] `git branch` affiche `* main`

### Après l'Étape 2/3

- [ ] `README.md` présent à la racine
- [ ] `docs/` contient `decisions.md` et `blocages.md` (supprimés ensuite)

### Après l'Étape 4

- [ ] `.gitignore` présent à la racine
- [ ] Dépôt distant GitHub configuré
- [ ] Branche `main` poussée vers GitHub

### Après l'Étape 5

- [ ] `docs/decisions.md` et `docs/blocages.md` supprimés
- [ ] `docs/documentation.md` créé

### Après l'Étape 6

- [ ] `.env.example` créé avec `FIRMS_MAP_KEY=` et `POSTGRES_PASSWORD=`
- [ ] `.env` créé localement (non versionné)
- [ ] `.gitignore` modifié — `.env.*` supprimé

### Après l'Étape 7

- [ ] `.venv/` créé et fonctionnel
- [ ] `requests`, `python-dotenv`, `psycopg2-binary` installés
- [ ] `requirements.txt` généré (7 lignes)

### Après l'Étape 8

- [ ] `scripts/test_firms_connection.py` exécuté avec succès (HTTP 200)
- [ ] Vraie limite `day_range` identifiée : 1-5
- [ ] `DAY_RANGE=5` fixé dans les scripts

### Après l'Étape 9

- [ ] `docker-compose.yml` créé dans `docker/`
- [ ] `surveillance_postgres` en cours d'exécution
- [ ] PostgreSQL 16.4 confirmé
- [ ] Port 5433 accessible

### Après l'Étape 10

- [x] `ingestion/pull_firms_to_postgres.py` créé
- [x] `storage/sql/001_create_fire_detections.sql` créé
- [x] Schéma SQL appliqué — table `fire_detections` vérifiée avec `\d`
- [x] Bug 1 corrigé (f-string sans espace → "user broly")
- [x] Bug 2 corrigé (parenthèse manquante → `UndefinedFunction`)
- [x] Cast explicite des champs numériques ajouté
- [x] Pipeline testé : 4 détections insérées
- [x] Idempotence validée : 2ᵉ lancement → 0 insertion (doublons absorbés)

### Checklist globale

- [x] Environnement Docker configuré (10 GiB alloués)
- [x] Conflits de ports identifiés et solutions prévues
- [x] Dépôt Git initialisé sur la branche `main`
- [x] Dépôt distant GitHub configuré
- [x] README.md en place
- [x] .gitignore en place et à jour
- [x] .env.example en place (modèle de configuration)
- [x] .env en place localement (secrets non versionnés)
- [x] Clé NASA FIRMS obtenue et validée
- [x] Environnement Python isolé (.venv) fonctionnel
- [x] requirements.txt à jour (7 dépendances)
- [x] API FIRMS testée — vraie limite day_range documentée
- [x] PostgreSQL/PostGIS déployé et fonctionnel (16.4)
- [x] Script d'injection créé et fonctionnel
- [x] Schéma SQL appliqué et vérifié
- [x] Bugs corrigés et documentés
- [x] Idempotence du pipeline validée
- [x] documentation.md à jour et fidèle à la réalité
- [ ] Historique Git propre et à jour (fichiers non commités en attente)
