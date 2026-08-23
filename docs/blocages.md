# Journal des blocages rencontrés

| Blocage | Cause | Contournement | Leçon retenue |
|---|---|---|---|
| Mémoire Docker par défaut insuffisante (5,78 Gio) | Limite fixée lors d'une configuration antérieure, indépendante de la RAM réelle | Relevée manuellement à 10,2 Gio via les paramètres Docker Desktop | Toujours vérifier l'allocation réelle avec `docker info` avant de dimensionner une architecture |
| Port 8080 potentiellement en conflit | Instance Airflow déjà active sur la machine | Remapping explicite prévu pour l'interface web Spark (ex. `8081:8080`) | En Docker partagé, auditer les ports déjà occupés avant de déployer un nouveau service |