# ADR-004 – Extraire `rentals` en microservice derrière une API gateway

- **Statut** : accepté (Unit 04). Remplace partiellement ADR-003.
- **Date** : 2026-10-28

## Contexte

Le module `rentals` évolue beaucoup plus vite que `books` : tarifs, nouveaux champs,
changement du contrat de prix. Avec le monolithe, chaque changement redéploie aussi le
catalogue.

Nous voulons aussi tester les nouvelles versions sur une partie du trafic (canary), ce qui
suppose de pouvoir faire tourner **deux versions de rentals en même temps**.

## Décision

- **`rentals` devient un service à part**, avec sa propre base (*database per service*).
  `books` reste l'ancien monolithe, avec sa configuration par environnement.
- **Une gateway NGINX est le seul point d'entrée.** Elle prend en charge :
  - l'authentification (`X-API-Key` → `X-User-Id`) ;
  - le rate limit ;
  - les erreurs en JSON ;
  - le **routage des releases** (`$rentals_pool`).
- **Aucun service ne publie de port**, sauf la gateway, plus MongoDB et Prometheus en
  `127.0.0.1` pour le lab.
- **Deux slots `rentals-blue` / `rentals-green`** partagent la base `rentals`. Le schéma
  reste compatible entre deux versions consécutives.

## Conséquences

Avantages :

- `rentals` se déploie seul.
- Les stratégies blue/green, canary et rolling deviennent possibles.
- La sécurité est centralisée.

Inconvénients :

- Plus de pièces à exploiter : 8 conteneurs.
- Les appels passent par le réseau.
- La gateway est un point unique de défaillance.
- **Piège** : NGINX résout les noms au démarrage. Il faut `resolver` + `resolve` pour
  suivre les conteneurs recréés.
