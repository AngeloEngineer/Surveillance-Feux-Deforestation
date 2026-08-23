# Journal des décisions techniques

| Décision | Alternatives envisagées | Justification | Étape |
|---|---|---|---|
| Docker Compose plutôt qu'un cluster physique | — | Seule option réaliste sans infrastructure dédiée | Cadrage initial |
| Facteur de réplication HDFS = 2 | 3 (valeur par défaut) | Espace disque disponible < 50 Go ; compromis assumé | Cadrage initial |
| Mémoire Docker relevée à 10,2 Gio | Rester à 5,78 Gio | 5,78 Gio insuffisant pour le cluster complet sans OOMKilled | Étape 0 |
| Nom de branche Git `main` | `master` (valeur par défaut) | Convention standard actuelle de l'industrie | Étape 1 |