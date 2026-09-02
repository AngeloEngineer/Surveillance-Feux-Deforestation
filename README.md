# Système de surveillance des feux de brousse et de la déforestation

## Problème

_[À compléter : description du problème concret — feux de brousse en Afrique de l'Ouest, double origine (brûlis volontaires et incendies incontrôlés), déforestation, besoin d'agir tôt]_

## Utilisateurs visés

- Gestionnaires d'aires protégées
- Services forestiers
- Acteurs agricoles locaux

## Architecture

_[À compléter : schéma de l'architecture globale, une fois les choix validés]_

| Composant | Rôle | Technologies | État |
|-----------|------|--------------|------|
| Ingestion | Récupérer les détections de feux depuis FIRMS | Python, requests, psycopg2 | Fonctionnel — testé, idempotence validée |
| Stockage | Stocker les données géospatiales | PostgreSQL 16.4, PostGIS 3.4 | Déployé, fonctionnel |
| Traitement | _[à définir]_ | _[à définir]_ | _[à définir]_ |
| Analytics | _[à définir]_ | _[à définir]_ | _[à définir]_ |

## Sources de données

| Source | Type | Fréquence | État |
|--------|------|-----------|------|
| NASA FIRMS (VIIRS_SNPP_NRT) | API REST, CSV | Quasi continue (5 jours glissants) | Testée, fonctionnelle |

## Contraintes d'environnement

| Contrainte | Valeur | Impact |
|------------|--------|--------|
| OS | Linux (Pop!_OS, base Ubuntu) | Environnement natif |
| RAM | 16 Go | Docker plafonné à 10,2 Gio |
| CPU | 4 cœurs (8 threads) | Limite les exécuteurs Spark parallèles |
| Disque | < 50 Go | Réplication HDFS = 2 |
| Docker | Partagé avec d'autres systèmes | Conflits de ports à gérer |
| Java | OpenJDK 17.0.19 | Compatibilité Hadoop/Spark à valider |

## Décisions techniques et blocages

_[À compléter au fil du projet — voir docs/documentation.md]_

## Structure du dépôt

```
surveillance-feux-deforestation/
├── .gitignore
├── .env.example
├── README.md
├── requirements.txt
├── docker/
│   └── docker-compose.yml
├── docs/
│   └── documentation.md
├── ingestion/
│   └── pull_firms_to_postgres.py
├── logs/
├── scripts/
│   └── test_firms_connection.py
└── storage/
    └── sql/
        └── 001_create_fire_detections.sql
```

## Démarrage

_[À compléter : instructions de démarrage une fois le pipeline opérationnel]_

## Limites connues

_[À compléter : uniquement après obtention de résultats réels]_
