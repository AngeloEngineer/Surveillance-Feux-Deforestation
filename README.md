# Système de surveillance des feux de brousse et de la déforestation

## Problème

_[À compléter : description du problème concret — feux de brousse en Afrique de l'Ouest, double origine (brûlis volontaires et incendies incontrôlés), déforestation, besoin d'agir tôt]_

## Utilisateurs visés

- Gestionnaires d'aires protégées
- Services forestiers
- Acteurs agricoles locaux

## Architecture

_[À compléter : schéma de l'architecture globale, une fois les choix validés]_

| Composant | Rôle | Technologies |
|-----------|------|--------------|
| Ingestion | _[à définir]_ | _[à définir]_ |
| Stockage | _[à définir]_ | _[à définir]_ |
| Traitement | _[à définir]_ | _[à définir]_ |
| Analytics | _[à définir]_ | _[à définir]_ |

## Sources de données

_[À compléter : types de sources, vélocité, origine]_

| Source | Type | Fréquence |
|--------|------|-----------|
| _[à définir]_ | _[à définir]_ | _[à définir]_ |

## Contraintes d'environnement

| Contrainte | Valeur | Impact |
|------------|--------|--------|
| OS | Linux (Pop!_OS, base Ubuntu) | Environnement natif |
| RAM | 16 Go | Docker plafonné à 10,2 Gio |
| CPU | 4 cœurs (8 threads) | Limite les exécuteurs Spark parallèles |
| Disque | < 50 Go | Réplication HDFS = 2 |
| Docker | Partagé avec d'autres systèmes | Conflits de ports à gérer |
| Java | OpenJDK 17.0.19 | Compatibilité Hadoop/Spark à valider |

## Décisions techniques

_[À compléter au fil du projet — voir docs/decisions.md]_

## Blocages rencontrés

_[À compléter au fil du projet — voir docs/blocages.md]_

## Structure du dépôt

```
surveillance-feux-deforestation/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── decisions.md
│   ├── blocages.md
│   └── donnees.md
├── ingestion/
├── storage/
├── processing/
├── analytics/
├── pipelines/
├── monitoring/
├── tests/
├── scripts/
├── notebooks/
└── docker/
```

## Démarrage

_[À compléter : instructions de démarrage une fois le pipeline opérationnel]_

## Limites connues

_[À compléter : uniquement après obtention de résultats réels]_
