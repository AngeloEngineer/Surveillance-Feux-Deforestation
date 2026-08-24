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
5. [Historique Git](#5-historique-git)
6. [Décisions techniques](#6-décisions-techniques)
7. [Blocages rencontrés](#7-blocages-rencontrés)
8. [Structure actuelle du dépôt](#8-structure-actuelle-du-dépôt)
9. [Reproduction depuis zéro](#9-reproduction-depuis-zéro)
10. [Informations manquantes](#10-informations-manquantes)
11. [Glossaire](#11-glossaire)
12. [Checklist de validation](#12-checklist-de-validation)

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

### Environnement partagé

Docker est partagé avec d'autres systèmes déjà en production locale. Lors de l'audit, les conteneurs suivants étaient actifs :

| Conteneur | Projet d'origine |
|-----------|-----------------|
| veille_prix_postgres | Pipeline de veille des prix agricoles |
| veille_prix_mongo | Pipeline de veille des prix agricoles |
| sikapay_metabase | Instance de visualisation |
| airflow-airflow-apiserver-1 | Instance Airflow |
| (+ 4 autres conteneurs airflow) | Instance Airflow |

**Consommation mesurée :** ~1.3 Gio utilisés sur 10.2 Gio, laissant ~8.9 Gio de marge pour le nouveau système.

### Point de vigilance — Conflit de port

| Port | Service actuel | Service futur en conflit | Solution retenue |
|------|---------------|-------------------------|------------------|
| 8080 | airflow-airflow-apiserver-1 (interface web Airflow) | Spark (interface web par défaut) | Remapping explicite : `8081:8080` pour Spark |

### Logiciels installés

| Logiciel | Version | Rôle dans le projet |
|----------|---------|---------------------|
| Docker | Non vérifié (⚠️ INFORMATION MANQUANTE) | Conteneurisation de l'ensemble du cluster |
| Docker Desktop | Non vérifié (⚠️ INFORMATION MANQUANTE) | Interface graphique de gestion Docker |
| Git | Non vérifié (⚠️ INFORMATION MANQUANTE) | Versioning du code source |
| OpenJDK | 17.0.19 | Runtime Java pour Hadoop/Spark |

---

## 4. Chronologie des étapes réalisées

---

### Étape 0 — Audit des ressources Docker

**Objectif**

Vérifier les ressources réellement disponibles pour Docker avant tout dimensionnement d'architecture. Cette étape est préalable à toute décision de conception du pipeline, car la capacité réelle de calcul détermine directement ce qui est faisable.

**Prérequis**

- Docker installé et démarré
- Accès en ligne de commande

**Actions**

1. Exécuter la commande d'audit des ressources Docker :

```bash
docker info | grep -E "CPUs|Total Memory"
```

2. Observer le résultat initial :

```
CPUs: 8
Total Memory: 5.784GiB
```

3. Analyser le résultat :
   - 8 CPU logiques = 4 cœurs physiques avec hyperthreading (cohérent avec l'architecture matérielle)
   - 5.78 GiB de RAM allouée à Docker est **insuffisante** pour le cluster prévu (HDFS + Kafka + Spark + PostgreSQL fonctionnant simultanément)

4. Augmenter manuellement la mémoire Docker via l'interface graphique :
   - Ouvrir Docker Desktop
   - Aller dans Settings > Resources > Memory
   - Modifier la valeur de 5.78 GiB à 10 GiB
   - Cliquer sur Apply & Restart

5. Vérifier le résultat après redémarrage :

```bash
docker info | grep -E "CPUs|Total Memory"
```

6. Observer le résultat corrigé :

```
CPUs: 8
Total Memory: 10.2GiB
```

7. Auditer l'environnement partagé — lister les conteneurs actifs :

```bash
docker ps
```

8. Mesurer la consommation réelle des conteneurs existants :

```bash
docker stats --no-stream
```

**Résultat attendu**

| Métrique | Avant | Après |
|----------|-------|-------|
| RAM Docker | 5.784 GiB | 10.2 GiB |
| Conteneurs actifs | 0 (projet) | 0 (projet) |
| Autres conteneurs | — | ~8 (veille_prix, Airflow, Metabase) |
| RAM disponible pour le projet | — | ~8.9 GiB |

**Vérification**

```bash
docker info | grep "Total Memory"
# Doit afficher : Total Memory: 10.2GiB
```

**Si cela échoue**

| Symptôme | Cause possible | Correction |
|----------|---------------|------------|
| Total Memory reste à 5.78 GiB | Docker Desktop n'a pas redémarré | Fermer Docker Desktop complètement, puis le relancer |
| Erreur "permission denied" | L'utilisateur n'a pas les droits Docker | Ajouter l'utilisateur au groupe docker : `sudo usermod -aG docker $USER`, puis se déconnecter/reconnecter |
| Docker Desktop ne démarre pas | Conflit avec un autre hyperviseur | Vérifier qu'aucun autre hyperviseur (VirtualBox, VMware) n'est actif |

**Critère de passage**

La commande `docker info | grep "Total Memory"` retourne `Total Memory: 10.2GiB`.

---

### Étape 1 — Initialisation du dépôt Git

**Objectif**

Créer le répertoire du projet et initialiser un dépôt Git pour le versioning du code source et de la documentation.

**Prérequis**

- Git installé et fonctionnel
- Espace disque disponible dans le répertoire cible

**Actions**

1. Créer le répertoire du projet :

```bash
mkdir ~/Mes_Projets/surveillance-feux-deforestation
```

2. Se déplacer dans le répertoire :

```bash
cd ~/Mes_Projets/surveillance-feux-deforestation
```

3. Initialiser le dépôt Git :

```bash
git init
```

4. Vérifier le résultat :

```bash
git status
```

5. Observer la branche par défaut :

```bash
git branch
```

Résultat initial :

```
* master
```

6. Renommer la branche en "main" (convention standard actuelle de l'industrie) :

```bash
git branch -m main
```

7. Vérifier le renommage :

```bash
git branch
```

Résultat attendu :

```
* main
```

**Résultat attendu**

- Répertoire `~/Mes_Projets/surveillance-feux-deforestation` créé
- Dépôt Git initialisé
- Branche par défaut renommée de `master` à `main`
- Répertoire vide (aucun fichier hormis `.git/`)

**Vérification**

```bash
ls -la ~/Mes_Projets/surveillance-feux-deforestation/
# Doit afficher : .git/ (dossier) et rien d'autre

git -C ~/Mes_Projets/surveillance-feux-deforestation branch
# Doit afficher : * main
```

**Si cela échoue**

| Symptôme | Cause possible | Correction |
|----------|---------------|------------|
| "fatal: not a git repository" | `git init` n'a pas été exécuté ou le répertoire courant est incorrect | Revenir à l'étape 3 et vérifier le chemin |
| "branch 'master' not found" | La branche a déjà été renommée ou le dépôt est vide avecHEAD non défini | Vérifier avec `git branch -a` |

**Critère de passage**

Le répertoire contient un dossier `.git/` et la branche active est `main`.

---

### Étape 2/3 — Scaffold README et premier commit

**Objectif**

Créer la structure initiale du projet avec un fichier README.md décrivant les grandes lignes du système, puis effectuer le premier commit pour snapshots l'état initial.

**Prérequis**

- Dépôt Git initialisé (Étape 1)
- Fichier `docs/` existant ou à créer

**Actions**

1. Créer le répertoire de documentation :

```bash
mkdir docs
```

2. Créer les fichiers de journal initiaux (approche subsequently abandoned, voir Étape 5) :

```bash
touch docs/decisions.md
touch docs/blocages.md
```

3. Créer le fichier README.md avec la structure suivante :

```bash
cat > README.md << 'EOF'
# Système de surveillance des feux de brousse et de la déforestation

## Problème
_[À compléter]_

## Utilisateurs visés
- Gestionnaires d'aires protégées
- Services forestiers
- Acteurs agricoles locaux

## Architecture
_[À compléter]_

## Sources de données
_[À compléter]_

## Contraintes d'environnement
_[À compléter]_

## Structure du dépôt
_[À compléter]_

## Démarrage
_[À compléter]_

## Limites connues
_[À compléter]_
EOF
```

4. Vérifier les fichiers créés :

```bash
ls -la
ls -la docs/
```

5. Ajouter les fichiers au staging :

```bash
git add README.md docs/
```

6. Vérifier le staging :

```bash
git status
```

7. Effectuer le premier commit :

```bash
git commit -m "Initialise la structure du projet et la documentation de cadrage"
```

8. Vérifier le commit :

```bash
git log --oneline
```

**Résultat attendu**

- Fichier `README.md` présent à la racine
- Répertoire `docs/` présent avec `decisions.md` et `blocages.md` (vides)
- Premier commit enregistré avec le hash `48f4a3a`

**Vérification**

```bash
git log --oneline
# Doit afficher : 48f4a3a Initialise la structure du projet et la documentation de cadrage

ls -la
# Doit afficher : README.md, docs/, .git/
```

**Critère de passage**

Le premier commit est enregistré et contient `README.md` et `docs/`.

---

### Étape 4 — Mise en place du .gitignore

**Objectif**

Empêcher le commit accidentel de secrets (clés API, mots de passe), de fichiers volumineux (données satellite, parquet), et de fichiers système non pertinents pour le projet.

**Prérequis**

- Dépôt Git initialisé (Étape 1)
- Premier commit effectué (Étape 2/3)

**Contexte de cette étape**

Avant toute manipulation de clé API (notamment la NASA FIRMS MAP_KEY qui sera nécessaire pour l'ingestion de données de détection de feux) ou d'environnement virtuel Python, il est impératif de sécuriser le dépôt contre les commits accidentels de secrets.

**Actions**

1. Créer le fichier `.gitignore` :

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.pyc
.venv/
venv/
*.egg-info/
.pytest_cache/
.mypy_cache/

# Secrets et configuration locale — ne jamais versionner
.env
.env.*
*.key
secrets/

# Données téléchargées localement (volumineuses, non versionnées)
data/raw/
data/interim/
*.tif
*.tiff
*.parquet
*.nc

# Docker (volumes montés localement si on en utilise)
docker/volumes/

# OS / éditeur
.DS_Store
Thumbs.db

# Logs
*.log
EOF
```

2. Vérifier le contenu du fichier :

```bash
cat .gitignore
```

3. Ajouter au staging :

```bash
git add .gitignore
```

4. Effectuer le commit :

```bash
git commit -m "Ajoute le fichier .gitignore"
```

5. Vérifier le commit :

```bash
git log --oneline
```

6. Pousser le commit vers le dépôt distant GitHub :

```bash
git push
```

> **Blocage rencontré :** La commande `git push` échoue avec l'erreur `fatal: Pas de destination pour pousser` car aucun dépôt distant n'est configuré.

7. Ajouter le dépôt distant GitHub :

```bash
git remote add origin https://github.com/AngeloEngineer/Surveillance-Feux-Deforestation.git
```

8. Pousser la branche `main` vers le dépôt distant et configurer le suivi :

```bash
git push -u origin main
```

**Sortie attendue :**

```
Énumération des objets: 9, fait.
Décompte des objets: 100% (9/9), fait.
Compression par delta en utilisant jusqu'à 8 fils d'exécution
Compression des objets: 100% (9/9), fait.
Écriture des objets: 100% (9/9), 2.74 Kio | 2.74 Mio/s, fait.
Total 9 (delta 0), réutilisés 0 (delta 0), réutilisés du pack 0
To https://github.com/AngeloEngineer/Surveillance-Feux-Deforestation.git
 * [new branch]      main -> main
la branche 'main' est paramétrée pour suivre 'origin/main'
```

9. Vérifier la configuration du dépôt distant :

```bash
git remote -v
```

**Sortie attendue :**

```
origin  https://github.com/AngeloEngineer/Surveillance-Feux-Deforestation.git (fetch)
origin  https://github.com/AngeloEngineer/Surveillance-Feux-Deforestation.git (push)
```

**Contenu du .gitignore — Explication par catégorie**

| Catégorie | Patterns exclus | Justification |
|-----------|----------------|---------------|
| Python | `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `*.egg-info/`, `.pytest_cache/`, `.mypy_cache/` | Fichiers générés par l'interpréteur Python et les outils de développement, non reproductibles sur une autre machine |
| Secrets | `.env`, `.env.*`, `*.key`, `secrets/` | Clés API, mots de passe, certificats — jamais versionnés par sécurité |
| Données volumineuses | `data/raw/`, `data/interim/`, `*.tif`, `*.tiff`, `*.parquet`, `*.nc` | Fichiers de données satellite (GeoTIFF), données intermédiaires (Parquet), données NetCDF — trop volumineux pour Git |
| Docker | `docker/volumes/` | Volumes Docker montés localement, contenant des données persistantes |
| OS/éditeur | `.DS_Store`, `Thumbs.db` | Fiers systèmes macOS/Windows, non pertinents |
| Logs | `*.log` | Fichiers de log pouvant contenir des informations sensibles ou devenir très volumineux |

**Résultat attendu**

- Fichier `.gitignore` présent à la racine du dépôt
- Deuxième commit enregistré
- Dépôt distant GitHub configuré
- Branche `main` poussée vers GitHub

**Vérification**

```bash
git log --oneline
# Doit afficher :
# 895cdff Ajoute le fichier .gitignore
# 48f4a3a Initialise la structure du projet et la documentation de cadrage

git remote -v
# Doit afficher l'URL du dépôt distant GitHub
```

**Critère de passage**

Le fichier `.gitignore` est présent, le deuxième commit est enregistré, et le dépôt distant GitHub est configuré.

---

### Étape 5 — Remplacement des journaux par documentation.md

**Objectif**

Remplacer les deux fichiers de journal séparés (`docs/decisions.md` et `docs/blocages.md`) par un fichier unique `docs/documentation.md` suivant une philosophie de documentation axée sur la reproductibilité intégrale.

**Prérequis**

- Fichiers `docs/decisions.md` et `docs/blocages.md` existants (créés à l'Étape 2/3)

**Décision technique**

| Élément | Détail |
|---------|--------|
| Décision | Abandon des journaux séparés au profit d'un document unique |
| Alternatives envisagées | Journaux séparés (décisions.md, blocages.md) |
| Justification | Un document narratif unique, intégrant décisions et blocages en contexte, est plus utile pour la reproductibilité qu'une série de tableaux déconnectés du raisonnement |
| Standard visé | Précision permettant une reproduction complète du projet par un lecteur à 30-45% de background |

**Actions**

1. Supprimer les fichiers de journal séparés :

```bash
git rm docs/decisions.md docs/blocages.md
```

2. Créer le fichier de documentation unique :

```bash
touch docs/documentation.md
```

3. Vérifier le résultat :

```bash
ls -la docs/
```

4. Ajouter au staging :

```bash
git add docs/
```

5. Effectuer le commit :

```bash
git commit -m "Remplace les journaux décisions/blocages par une documentation complète"
```

6. Vérifier le commit :

```bash
git log --oneline
```

7. Pousser le commit vers le dépôt distant GitHub :

```bash
git push
```

> **Note :** Le dépôt distant a été configuré lors de l'Étape 4. La commande `git push` fonctionne directement car le suivi de branche a été établi avec `git push -u origin main`.

**Résultat attendu**

- `docs/decisions.md` supprimé du dépôt
- `docs/blocages.md` supprimé du dépôt
- `docs/documentation.md` créé (vide à ce stade, à alimenter)
- Troisième commit enregistré
- Commit poussé vers GitHub

**Vérification**

```bash
ls docs/
# Doit afficher uniquement : documentation.md

git log --oneline
# Doit afficher :
# 4817ffe Remplace les journaux décisions/blocages par une documentation complète
# 895cdff Ajoute le fichier .gitignore
# 48f4a3a Initialise la structure du projet et la documentation de cadrage
```

**Critère de passage**

Les fichiers `decisions.md` et `blocages.md` n'existent plus, et `documentation.md` est présent.

---

## 5. Historique Git

### Branche principale

| Hash court | Message de commit | Étape correspondante |
|------------|-------------------|---------------------|
| `48f4a3a` | Initialise la structure du projet et la documentation de cadrage | Étape 2/3 |
| `895cdff` | Ajoute le fichier .gitignore | Étape 4 |
| `4817ffe` | Remplace les journaux décisions/blocages par une documentation complète | Étape 5 |

### Branche active

- Nom : `main`
- Branche par défaut renommée depuis `master` lors de l'Étape 1

### Dépôt distant

| Paramètre | Valeur |
|-----------|--------|
| Nom | `origin` |
| URL | `https://github.com/AngeloEngineer/Surveillance-Feux-Deforestation.git` |
| Branche suivie | `main` |

### Commandes de push exécutées

```bash
# Tentative de push sans dépôt distant configuré (a échoué)
git push
# Erreur : fatal: Pas de destination pour pousser.

# Ajout du dépôt distant
git remote add origin https://github.com/AngeloEngineer/Surveillance-Feux-Deforestation.git

# Push avec configuration du suivi de branche
git push -u origin main
```

### État après push

- Les 3 commits ont été poussés vers GitHub
- La branche `main` est paramétrée pour suivre `origin/main`
- Les push ultérieurs fonctionnent avec `git push` sans argument

---

## 6. Décisions techniques

| # | Décision | Alternatives envisagées | Justification | Étape | Date |
|---|----------|------------------------|---------------|-------|------|
| D1 | Docker Compose plutôt qu'un cluster physique | — | Seule option réaliste sans infrastructure dédiée, permet de simuler un environnement multi-nœuds sur une seule machine | Cadrage initial | Non documenté |
| D2 | Facteur de réplication HDFS = 2 | 3 (valeur par défaut) | Espace disque disponible < 50 Go ; compromis assumé entre résilience et contrainte matérielle | Cadrage initial | Non documenté |
| D3 | Mémoire Docker relevée à 10 GiB | Rester à 5.78 GiB (valeur par défaut initiale) | 5.78 GiB insuffisant pour faire tourner le cluster complet sans OOMKilled | Étape 0 | Non documenté |
| D4 | Nom de branche Git `main` | `master` (valeur par défaut de Git) | Convention standard actuelle de l'industrie | Étape 1 | Non documenté |
| D5 | Documentation unique (documentation.md) plutôt que journaux séparés (decisions.md, blocages.md) | Journaux séparés | Un document narratif unique intégrant décisions et blocages en contexte est plus utile pour la reproductibilité | Étape 5 | Non documenté |
| D6 | Dépôt distant GitHub configuré après le premier push raté | Push immédiat après le commit | Le push a échoué car aucun dépôt distant n'était configuré ; le dépôt a été ajouté manuellement | Étape 4 | Non documenté |

---

## 7. Blocages rencontrés

| # | Blocage | Cause | Contournement appliqué | Leçon retenue | Étape |
|---|---------|-------|----------------------|---------------|-------|
| B1 | Mémoire Docker par défaut insuffisante (5.78 GiB) | Limite fixée lors d'une configuration antérieure, indépendante de la RAM réelle de la machine | Relevée manuellement à 10 GiB via les paramètres Docker Desktop | Toujours vérifier l'allocation réelle avec `docker info` avant de dimensionner une architecture, ne jamais la supposer | Étape 0 |
| B2 | Port 8080 potentiellement en conflit | Une instance Airflow déjà active sur la machine occupe ce port | Remapping explicite prévu pour l'interface web Spark (ex. `8081:8080`) | En environnement Docker partagé, auditer systématiquement les ports déjà occupés avant de déployer un nouveau service | Étape 0 |
| B3 | Push Git échoué — pas de destination | Aucun dépôt distant configuré lors de la première tentative de push | Ajout manuel du dépôt distant GitHub puis push avec `-u` pour configurer le suivi | Toujours vérifier `git remote -v` avant de pousser, ou configurer le dépôt distant dès l'initialisation du projet | Étape 4 |

---

## 8. Structure actuelle du dépôt

```
surveillance-feux-deforestation/
├── .git/                    # Dépôt Git
├── .gitignore               # Règles d'exclusion pour Git
├── README.md                # Description du projet
└── docs/
    └── documentation.md     # Ce fichier
```

### Fichiers versionnés

| Fichier | Taille | Rôle |
|---------|--------|------|
| `.gitignore` | Non mesuré | Exclut les secrets, données volumineuses et fichiers système |
| `README.md` | 2221 octets | Description synthétique du projet |
| `docs/documentation.md` | Ce fichier | Documentation technique complète |

---

## 9. Reproduction depuis zéro

### Prérequis

| Outil | Version requise | Comment vérifier | Comment installer si absent |
|-------|----------------|------------------|----------------------------|
| Linux | Distribution basée Ubuntu (Pop!_OS recommandé) | `lsb_release -a` | Installer Pop!_OS depuis https://pop.system76.com |
| Docker | Dernière version stable | `docker --version` | Installer Docker Engine : https://docs.docker.com/engine/install/ubuntu |
| Docker Desktop | Dernière version stable | Vérifier l'icône dans le tray system | Installer depuis https://www.docker.com/products/docker-desktop |
| Git | Dernière version stable | `git --version` | `sudo apt install git` |
| Java | OpenJDK 17 | `java --version` | `sudo apt install openjdk-17-jdk` |

### Procédure

1. Installer les prérequis ci-dessus
2. Allouer 10 GiB à Docker (Settings > Resources > Memory)
3. Auditer les ports occupés : `docker ps` — vérifier qu'aucun service ne bloque le port 8080
4. Créer le répertoire : `mkdir ~/Mes_Projets/surveillance-feux-deforestation`
5. Initialiser Git : `cd ~/Mes_Projets/surveillance-feux-deforestation && git init && git branch -m main`
6. Cloner ou recréer les fichiers du dépôt
7. Vérifier : `git log --oneline` doit afficher les 3 commits

---

## 10. Informations manquantes

| Information | Pourquoi elle est nécessaire | Comment la récupérer |
|-------------|----------------------------|---------------------|
| Version exacte de Docker installé | Compatibilité avec les images Docker à utiliser | `docker --version` |
| Version exacte de Docker Desktop | Connaissance de la configuration des ressources | Vérifier dans l'interface Docker Desktop |
| Version exacte de Git | Compatibilité avec les fonctionnalités utilisées | `git --version` |
| Espace disque réellement disponible | Dimensionnement précis du cluster | `df -h /` |
| Liste complète des conteneurs Docker actifs | Audit de l'environnement partagé complet | `docker ps -a` |
| Résultat de `docker stats --no-stream` complet | Mesure précise de la consommation mémoire de chaque conteneur | Exécuter `docker stats --no-stream` et capturer la sortie |

---

## 11. Glossaire

| Terme | Définition | Rôle dans ce projet |
|-------|-----------|---------------------|
| HDFS | Hadoop Distributed File System — système de fichiers distribué | Stockage des données à grande échelle avec réplication |
| Kafka | Plateforme de streaming distribué | Ingestion en temps réel des flux de données |
| Spark | Moteur de traitement distribué | Traitement et analyse des données |
| Docker | Plateforme de conteneurisation | Isolation et déploiement des composants |
| Docker Compose | Outil de définition et orchestration multi-conteneurs | Définition de l'architecture complète du cluster |
| GeoTIFF | Format d'image satellite géoréférencée | Stockage des données d'imagerie satellite |
| Parquet | Format de stockage colonnaire optimisé | Stockage des données intermédiaires traitées |
| NetCDF | Format de données scientifiques multi-dimensionnelles | Données climatiques et environnementales |
| NASA FIRMS | Fire Information for Resource Management System | Source de données de détection de feux |
| MAP_KEY | Clé d'API pour accéder aux données NASA FIRMS | Authentification pour l'ingestion de données |
| OOMKilled | Out Of Memory Killed — processus tué par le système pour manque de mémoire | Risque principal si l'allocation Docker est insuffisante |

---

## 12. Checklist de validation

### Après l'Étape 0

- [ ] `docker info | grep "Total Memory"` affiche `10.2GiB`
- [ ] `docker ps` montre les conteneurs existants (veille_prix, Airflow, etc.)
- [ ] `docker stats --no-stream` confirme ~1.3 Gio utilisé, ~8.9 Gio disponible

### Après l'Étape 1

- [ ] Répertoire `~/Mes_Projets/surveillance-feux-deforestation` existe
- [ ] `git branch` affiche `* main`

### Après l'Étape 2/3

- [ ] `README.md` présent à la racine
- [ ] `docs/` contient `decisions.md` et `blocages.md`
- [ ] `git log --oneline` affiche le commit `48f4a3a`

### Après l'Étape 4

- [ ] `.gitignore` présent à la racine
- [ ] `git log --oneline` affiche le commit `895cdff`

### Après l'Étape 5

- [ ] `docs/decisions.md` n'existe plus
- [ ] `docs/blocages.md` n'existe plus
- [ ] `docs/documentation.md` est présent
- [ ] `git log --oneline` affiche le commit `4817ffe`

### Checklist globale

- [ ] Environnement Docker configuré (10 GiB alloués)
- [ ] Conflits de ports identifiés et solutions prévues
- [ ] Dépôt Git initialisé sur la branche `main`
- [ ] README.md en place
- [ ] .gitignore en place
- [ ] documentation.md en place et alimenté
- [ ] Historique Git propre et lisible
